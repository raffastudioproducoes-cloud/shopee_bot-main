"""O scheduler legado pode ser importado sem a configuração privada da API."""
import sys
from types import SimpleNamespace


def test_daily_analytics_job_imports_api_only_when_executed(monkeypatch):
    from shopee_bot import scheduler

    seen = []
    monkeypatch.setitem(
        sys.modules,
        "api.analytics_refresh",
        SimpleNamespace(refresh_due_analytics=lambda: seen.append("executed")),
    )
    scheduler._run_daily_analytics_refresh()
    assert seen == ["executed"]
