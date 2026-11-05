"""Contratos de ordenação por campanhas ativadas, sem acessar o Supabase real."""
import ast
import asyncio
import pathlib
from types import SimpleNamespace
import unittest


ROUTER_PATH = pathlib.Path(__file__).resolve().parents[2] / "api" / "routers" / "lists.py"
SOURCE = ROUTER_PATH.read_text(encoding="utf-8")
MODULE = ast.parse(SOURCE)
HELPER = next(
    node for node in MODULE.body
    if isinstance(node, ast.FunctionDef) and node.name == "_count_activated_list_ids"
)
SCOPE = {}
exec(compile(ast.Module(body=[HELPER], type_ignores=[]), str(ROUTER_PATH), "exec"), SCOPE)
count_ids = SCOPE["_count_activated_list_ids"]


class ListUsageSortContract(unittest.TestCase):
    def test_one_activation_counts_once_per_reservation_not_by_posts(self):
        rows = [
            {"source_list_id": "12"},
            {"source_list_id": "12"},
            {"source_list_id": 7},
            {"source_list_id": None},
            {"source_list_id": "invalid"},
            {"source_list_id": "-2"},
        ]
        self.assertEqual(count_ids(rows), {"12": 2, "7": 1})

    def test_empty_usage_is_zero(self):
        self.assertEqual(count_ids([]), {})

    def test_reads_only_activated_campaigns_and_scopes_ownership(self):
        endpoint = SOURCE.split('@router.get("/usage")', 1)[1].split('@router.post("")', 1)[0]
        self.assertIn('.eq("user_id", str(user_id))', endpoint)
        self.assertIn('.eq("profile_id", profile_id)', endpoint)
        self.assertIn('.not_.is_("activated_at", "null")', endpoint)
        self.assertIn('source_list_id:draft_snapshot->>source_list_id', endpoint)
        self.assertIn('.range(offset, offset + page_size - 1)', endpoint)
        self.assertNotIn('.insert(', endpoint)
        self.assertNotIn('.update(', endpoint)
        self.assertNotIn('.delete(', endpoint)

    def test_usage_static_route_precedes_dynamic_id(self):
        self.assertLess(SOURCE.index('@router.get("/usage")'), SOURCE.index('@router.get("/{product_list_id}")'))

    def test_endpoint_paginates_history_and_applies_user_profile_filters(self):
        class FakeQuery:
            def __init__(self):
                self.filters = []
                self.not_ = self
                self.range_calls = []

            def select(self, fields):
                self.selected = fields
                return self

            def eq(self, field, value):
                self.filters.append((field, value))
                return self

            def is_(self, field, value):
                self.filters.append((field, value))
                return self

            def order(self, field):
                self.order_field = field
                return self

            def range(self, start, end):
                self.range_calls.append((start, end))
                self.current_start = start
                return self

            def execute(self):
                return SimpleNamespace(data=([{"source_list_id": "12"}] * 500)
                                       if self.current_start == 0
                                       else [{"source_list_id": "12"}, {"source_list_id": "7"}])

        query = FakeQuery()

        class FakeSupabase:
            def table(self, name):
                if name != "campaign_reservations_f4e":
                    raise AssertionError("A API só pode ler reservas de campanhas")
                return query

        endpoint = next(node for node in MODULE.body
                        if isinstance(node, ast.AsyncFunctionDef)
                        and node.name == "get_product_list_usage")
        endpoint.decorator_list = []
        scope = {
            "Depends": lambda value: None,
            "get_current_user_id": lambda: None,
            "get_current_profile_id": lambda: None,
            "supabase": FakeSupabase(),
            "_count_activated_list_ids": count_ids,
        }
        exec(compile(ast.Module(body=[endpoint], type_ignores=[]), str(ROUTER_PATH), "exec"), scope)
        result = asyncio.run(scope["get_product_list_usage"]("user-42", "profile-99"))
        self.assertEqual(result, {"counts": {"12": 501, "7": 1}})
        self.assertEqual(query.range_calls, [(0, 499), (500, 999)])
        self.assertIn(("user_id", "user-42"), query.filters)
        self.assertIn(("profile_id", "profile-99"), query.filters)
        self.assertIn(("activated_at", "null"), query.filters)
        self.assertEqual(query.selected, "source_list_id:draft_snapshot->>source_list_id")


if __name__ == "__main__":
    unittest.main()
