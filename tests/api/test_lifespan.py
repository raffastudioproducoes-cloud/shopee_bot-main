"""O startup/shutdown da API usa lifespan (on_event está deprecado)."""
import asyncio
import warnings

from fastapi.testclient import TestClient

from api import main


def test_app_uses_lifespan_instead_of_deprecated_on_event():
    assert main.app.router.on_startup == []
    assert main.app.router.on_shutdown == []


def test_lifespan_starts_and_cancels_background_cleanup(monkeypatch):
    events = {"init": 0, "cancelled": False}

    async def fake_cleanup():
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            events["cancelled"] = True
            raise

    monkeypatch.setattr(main, "init_db", lambda: events.__setitem__("init", events["init"] + 1))
    monkeypatch.setattr(main, "_cleanup_media_drafts_periodically", fake_cleanup)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        with TestClient(main.app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert events["init"] == 1
            assert main.app.state.media_draft_cleanup_task is not None
    assert events["cancelled"] is True


def test_lifespan_survives_missing_supabase(monkeypatch):
    def broken_init():
        raise RuntimeError("sem supabase")

    monkeypatch.setattr(main, "init_db", broken_init)
    if hasattr(main.app.state, "media_draft_cleanup_task"):
        del main.app.state.media_draft_cleanup_task
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
    assert getattr(main.app.state, "media_draft_cleanup_task", None) is None
