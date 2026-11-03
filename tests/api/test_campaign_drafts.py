"""F3A: contrato de rascunho persistente, sem ativar scheduler ou Storage."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routers import campaigns


def item(product_id=12, **changes):
    values = dict(product_id=product_id, title="Produto", copy="",
                  affiliate_link="", networks=["threads"],
                  network_copies={"threads": ""}, use_shopee_image=True)
    values.update(changes)
    return values


def payload(**changes):
    values = dict(name="Ofertas de Novembro", list_id=11, items=[item(12), item(13)],
                  schedule=None)
    values.update(changes)
    return campaigns.CampaignDraftSave(**values)


def test_draft_does_not_accept_ids_from_another_list_or_duplicates():
    with pytest.raises(ValueError, match="exatamente"):
        campaigns.validate_campaign_draft_items([item(12), item(999)], [12, 13])
    with pytest.raises(ValueError, match="repetições"):
        campaigns.validate_campaign_draft_items([item(12), item(12)], [12, 13])


def test_draft_preserves_intentionally_empty_copy_and_rejects_invalid_network():
    saved = payload()
    assert saved.items[0].copy == ""
    assert saved.items[0].network_copies["threads"] == ""
    with pytest.raises(Exception):
        payload(items=[item(12, networks=["kwai"]), item(13)])


class _InsertQuery:
    def __init__(self, records):
        self.records = records
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        self.records.append(self.row)
        return SimpleNamespace(data=[{**self.row, "id": "draft-1", "revision": 1}])


class _DB:
    def __init__(self):
        self.writes = []
        self.table_names = []

    def table(self, name):
        self.table_names.append(name)
        return _InsertQuery(self.writes)


def test_create_draft_scopes_account_and_profile_without_creating_posts(monkeypatch):
    monkeypatch.setattr(campaigns, "_get_list",
                        lambda uid, lid, pid: {"id": lid, "name": "Minha lista",
                                               "user_id": uid, "profile_id": pid})
    monkeypatch.setattr(campaigns, "_get_list_products",
                        lambda lid: [{"id": 12, "image": "https://img.test/a"},
                                     {"id": 13, "image": "https://img.test/b"}])
    fake = _DB()
    monkeypatch.setattr(campaigns, "supabase", fake, raising=False)
    result = asyncio.run(campaigns.create_campaign_draft(payload(), user_id="owner", profile_id="profile-a"))
    assert result["id"] == "draft-1"
    assert fake.table_names == ["campaign_drafts"]
    assert fake.writes[0]["campaign_name"] == "Ofertas de Novembro"
    assert fake.writes[0]["user_id"] == "owner"
    assert fake.writes[0]["profile_id"] == "profile-a"
    assert [x["product_id"] for x in fake.writes[0]["items"]] == [12, 13]


def test_create_draft_rejects_missing_profile_before_any_write(monkeypatch):
    fake = _DB()
    monkeypatch.setattr(campaigns, "supabase", fake, raising=False)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.create_campaign_draft(payload(), user_id="owner", profile_id=None))
    assert caught.value.status_code == 400
    assert fake.writes == []

def test_schedule_must_match_saved_list_and_exact_product_order():
    schedule = campaigns.CampaignPreviewRequest(
        list_id=11, item_ids=[12, 13], start_date="2026-11-04",
        end_date="2026-11-06", weekdays=[0, 1, 2, 3, 4],
        start_time="09:00", end_time="18:00", posts_per_day=4,
    )
    campaigns.validate_campaign_draft_schedule(schedule, 11, [12, 13])
    with pytest.raises(ValueError, match="lista"):
        campaigns.validate_campaign_draft_schedule(schedule, 77, [12, 13])
    with pytest.raises(ValueError, match="ordem"):
        campaigns.validate_campaign_draft_schedule(schedule, 11, [13, 12])


def test_migration_070_is_safe_on_second_boot():
    """O migrador da aplicação executa SQL pendente no startup, inclusive após MCP."""
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[2] / "database/migrations/070_campaign_drafts.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.campaign_drafts" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_campaign_drafts_owner_updated" in sql
    assert "pg_catalog.pg_trigger" in sql
    assert "tgname = 'trg_campaign_draft_owner'" in sql
    assert "IF NOT EXISTS (" in sql
    assert "DROP TABLE" not in sql


def test_campaign_name_is_required_trimmed_and_independent_from_list():
    assert payload(name="  Black Friday  ").name == "Black Friday"
    with pytest.raises(Exception):
        payload(name="  ")
    with pytest.raises(Exception):
        payload(name="x" * 121)
    updated = campaigns.CampaignDraftUpdate(
        name="Minha campanha", expected_revision=1, items=[item(12), item(13)])
    assert updated.name == "Minha campanha"


def test_media_never_accepts_product_outside_draft():
    draft = {"status": "draft", "items": [item(12), item(13)]}
    campaigns._assert_draft_product(draft, 13)
    with pytest.raises(HTTPException) as caught:
        campaigns._assert_draft_product(draft, 999)
    assert caught.value.status_code == 404


def test_migration_071_is_reentrant_and_leaves_existing_posts_untouched():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[2] / "database/migrations/071_campaign_names_and_media.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS campaign_name" in sql
    assert "CREATE TABLE IF NOT EXISTS public.campaign_draft_media" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_campaign_draft_media_owner" in sql
    assert "tgname = 'trg_campaign_media_owner'" in sql
    assert "pg_catalog.pg_trigger" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL PRIVILEGES ON TABLE public.campaign_draft_media FROM anon, authenticated" in sql
    assert "DROP TABLE" not in sql
    assert "public.posts " not in sql


def test_campaign_media_upload_is_sanitized_private_scoped_and_never_creates_post(monkeypatch):
    from contextlib import nullcontext
    from uuid import UUID

    class Query:
        def __init__(self, db, name):
            self.db, self.name, self.action, self.payload = db, name, "select", None
        def select(self, *args): self.action = "select"; return self
        def eq(self, *args): return self
        def in_(self, *args): return self
        def lt(self, *args): return self
        def limit(self, *args): return self
        def insert(self, row): self.action, self.payload = "insert", row; return self
        def update(self, row): self.action, self.payload = "update", row; return self
        def execute(self):
            if self.action == "select": return SimpleNamespace(data=[])
            if self.action == "insert":
                self.db.record = dict(self.payload)
                return SimpleNamespace(data=[self.db.record.copy()])
            self.db.record.update(self.payload)
            return SimpleNamespace(data=[self.db.record.copy()])

    class Storage:
        def __init__(self): self.files = []
        def from_(self, bucket):
            assert bucket == "post-media"
            return self
        def upload(self, key, content, options):
            assert key.startswith("campaigns/owner/profile-a/")
            assert options["upsert"] == "false"
            self.files.append((key, content))

    class DB:
        def __init__(self):
            self.tables = []
            self.storage = Storage()
            self.record = None
        def table(self, name):
            self.tables.append(name)
            assert name == "campaign_draft_media"
            return Query(self, name)

    async def read_file(file): return b"raw"
    async def sanitize_file(file, content):
        assert content == b"raw"
        return SimpleNamespace(content=b"sanitized", mime_type="image/png",
                               extension=".png", media_type="IMAGE", safe_filename="foto.png")

    fake = DB()
    monkeypatch.setattr(campaigns, "supabase", fake)
    monkeypatch.setattr(campaigns, "scope_owner", lambda query, uid, pid: query)
    monkeypatch.setattr(campaigns, "_get_owned_campaign",
                        lambda draft_id, uid, pid: {"status": "draft", "items": [item(12)]})
    monkeypatch.setattr(campaigns, "_cleanup_abandoned_campaign_media", lambda *args: None)
    monkeypatch.setattr(campaigns, "_read_media_content", read_file)
    monkeypatch.setattr(campaigns, "_sanitize_upload", sanitize_file)
    monkeypatch.setattr(campaigns, "storage_upload_reservation", lambda length: nullcontext())

    result = asyncio.run(campaigns.upload_campaign_media(
        UUID("11111111-1111-1111-1111-111111111111"), 12, file=object(),
        user_id="owner", profile_id="profile-a"))
    assert result["file_name"] == "foto.png"
    assert result["status"] == "ready"
    assert result["product_id"] == 12
    assert fake.record["user_id"] == "owner"
    assert fake.record["profile_id"] == "profile-a"
    assert fake.storage.files[0][1] == b"sanitized"
    assert set(fake.tables) == {"campaign_draft_media"}
    assert "storage_key" not in result



def test_delete_draft_cleans_private_media_first_and_never_touches_posts(monkeypatch):
    from uuid import UUID

    draft_id = UUID("11111111-1111-1111-1111-111111111111")
    files = [{
        "id": "media-1", "storage_bucket": "post-media",
        "storage_key": f"campaigns/owner/profile-a/{draft_id}/12/file.png",
        "status": "ready",
    }]

    class Query:
        def __init__(self, db, name):
            self.db, self.name, self.cols, self.operation = db, name, "*", "select"
            self.filters = []
        def select(self, cols): self.cols = cols; return self
        def eq(self, key, value): self.filters.append((key, value)); return self
        def limit(self, count): return self
        def delete(self): self.operation = "delete"; return self
        def execute(self):
            if self.operation == "delete":
                assert self.db.events == [("storage.remove", [files[0]["storage_key"]])]
                assert ("revision", 3) in self.filters
                self.db.events.append(("db.delete", self.name))
                return SimpleNamespace(data=[{"id": str(draft_id)}])
            if self.name == "campaign_draft_media":
                return SimpleNamespace(data=([{"id": x["id"]} for x in files]
                                             if self.cols == "id" else files))
            raise AssertionError("Tabela não esperada")

    class Storage:
        def __init__(self, db): self.db = db
        def from_(self, bucket):
            assert bucket == "post-media"
            return self
        def remove(self, keys): self.db.events.append(("storage.remove", keys))

    class DB:
        def __init__(self):
            self.events = []
            self.storage = Storage(self)
        def table(self, name):
            assert name in ("campaign_drafts", "campaign_draft_media")
            return Query(self, name)

    fake = DB()
    scopes = []
    monkeypatch.setattr(campaigns, "supabase", fake)
    monkeypatch.setattr(campaigns, "_get_owned_campaign", lambda *_: {"status": "draft", "revision": 3})
    monkeypatch.setattr(campaigns, "scope_owner", lambda query, uid, pid: (
        scopes.append((uid, pid)) or query))
    result = asyncio.run(campaigns.delete_campaign_draft(
        draft_id, expected_revision=3, user_id="owner", profile_id="profile-a"))
    assert result is None
    assert fake.events[-1] == ("db.delete", "campaign_drafts")
    assert scopes == [("owner", "profile-a")] * 3


def test_delete_draft_refuses_stale_revision_without_storage_side_effects(monkeypatch):
    from uuid import UUID
    monkeypatch.setattr(campaigns, "_get_owned_campaign",
                        lambda *_: {"status": "draft", "revision": 4})
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.delete_campaign_draft(
            UUID("11111111-1111-1111-1111-111111111111"),
            expected_revision=3, user_id="owner", profile_id="profile-a"))
    assert caught.value.status_code == 409


def test_delete_draft_preserves_database_when_storage_cleanup_fails(monkeypatch):
    from uuid import UUID
    draft_id = UUID("11111111-1111-1111-1111-111111111111")
    events = []

    class Query:
        def select(self, *args): return self
        def eq(self, *args): return self
        def limit(self, *args): return self
        def delete(self):
            raise AssertionError("Não deve apagar a campanha após erro no Storage")
        def execute(self):
            return SimpleNamespace(data=[{
                "id": "media-1", "storage_bucket": "post-media",
                "storage_key": f"campaigns/owner/profile-a/{draft_id}/12/file.png",
                "status": "ready",
            }])

    class Storage:
        def from_(self, bucket): return self
        def remove(self, keys):
            events.append("attempt")
            raise RuntimeError("storage offline")

    class DB:
        storage = Storage()
        def table(self, name):
            assert name == "campaign_draft_media"
            return Query()

    monkeypatch.setattr(campaigns, "supabase", DB())
    monkeypatch.setattr(campaigns, "_get_owned_campaign",
                        lambda *_: {"status": "draft", "revision": 1})
    monkeypatch.setattr(campaigns, "scope_owner", lambda query, *_: query)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(campaigns.delete_campaign_draft(
            draft_id, expected_revision=1, user_id="owner", profile_id="profile-a"))
    assert caught.value.status_code == 502
    assert events == ["attempt"]
