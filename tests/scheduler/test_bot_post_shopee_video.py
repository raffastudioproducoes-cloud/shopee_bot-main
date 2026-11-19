"""Publicador Shopee Vídeo: tudo mockado (sem banco, Storage ou Shopee reais)."""

import contextlib
import os
import sys

import pytest

# api.config exige segredo de JWT ao importar a API nova (só para o teste).
os.environ.setdefault("API_SECRET_KEY", "test-only-api-secret-key-0123456789abcdef-0123456789abcdef-padding-64b")

import shopee_bot.scheduler.bot_post_shopee_video  # noqa: E402,F401
from shopee_bot.apis import shopee_video as sv  # noqa: E402

module = sys.modules["shopee_bot.scheduler.bot_post_shopee_video"]
tokens = module._tokens()

AUTH = tokens.ValidAuthorization(123, "test-key", 98765, "fresh-access", True)
VIDEO = {"type": "VIDEO", "file_name": "v.mp4", "file_path": "storage://post-media/v.mp4", "size": 8}


class FakeClient:
    """Registra a sequência de chamadas; `fail` = {método: exceção}."""

    instances = []

    def __init__(self, authorization, *, sandbox, enabled, session=None):
        assert enabled is True and authorization.permission_granted is True
        assert authorization.access_token == "fresh-access" and sandbox is True
        self.calls, self.fail, self.found = [], dict(FakeClient.fail), FakeClient.found
        FakeClient.instances.append(self)

    def _maybe_fail(self, name):
        self.calls.append(name)
        if name in self.fail:
            raise self.fail[name]

    def upload_file(self, stream, name, size, duration):
        self._maybe_fail("upload_file")
        self.duration = duration
        return "upload-1"

    def wait_upload_result(self, upload_id, **_kw):
        self._maybe_fail("wait_upload_result")
        return "SUCCEEDED"

    def get_covers(self, upload_id):
        self._maybe_fail("get_covers")
        return ["https://cf.shopee.test/cover.jpg"]

    def set_video_info(self, upload_id, **kwargs):
        self._maybe_fail("set_video_info")
        self.info = kwargs

    def post_video(self, upload_id, **_kw):
        self._maybe_fail("post_video")
        return {"video_upload_id": upload_id, "confirmation": [{"video_id": "sv-777"}]}

    def find_posted_video(self, upload_id):
        self._maybe_fail("find_posted_video")
        return self.found


@pytest.fixture(autouse=True)
def _base(monkeypatch, tmp_path):
    FakeClient.instances, FakeClient.fail, FakeClient.found = [], {}, None
    video = tmp_path / "v.mp4"
    video.write_bytes(b"12345678")
    monkeypatch.setattr(module.schedulers, "get_by_id",
                        lambda job_id: {"user_id": 42, "post_id": 7, "profile_id": "profile-1"})
    monkeypatch.setattr(module.posts, "get", lambda *a: [{"text": "Achado do dia", "medias": [VIDEO]}])
    monkeypatch.setattr(module.posts, "get_shopee_item_ids", lambda *a: [111, 222, 111, 0])
    monkeypatch.setattr(tokens, "get_valid_authorization", lambda *a: AUTH)
    monkeypatch.setattr(module, "ShopeeVideoClient", FakeClient)
    monkeypatch.setattr(module, "video_duration_seconds", lambda path: 15.4)
    monkeypatch.setattr(module, "mark_external_delivery", lambda: FakeClient.instances[-1].calls.append("mark"))

    @contextlib.contextmanager
    def local(media, max_bytes):
        assert max_bytes == sv.MAX_VIDEO_SIZE
        yield str(video)

    monkeypatch.setattr(module, "local_file", local)
    activities = []
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: activities.append(a))
    return activities


def _meta(activities):
    return activities[-1][2]


def test_success_uploads_links_products_and_posts_once(_base):
    result = module.bot_post_shopee_video("job-1")
    assert (result.status, result.external_id) == ("succeeded", "sv-777")
    client = FakeClient.instances[0]
    assert client.calls == ["upload_file", "wait_upload_result", "get_covers", "set_video_info",
                            "mark", "post_video"]
    assert client.duration == 15
    assert client.info["product_item_ids"] == [111, 222]
    assert client.info["cover_url"] == "https://cf.shopee.test/cover.jpg"
    assert client.info["caption"] == "Achado do dia" and client.info["ai_assisted"] is False


def test_without_video_fails_before_any_shopee_call(monkeypatch, _base):
    monkeypatch.setattr(module.posts, "get", lambda *a: [{"text": "oi", "medias": []}])
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "failed" and "vídeo" in result.error
    assert FakeClient.instances == []


def test_without_connection_fails_with_reconnect_message(monkeypatch, _base):
    def reconnect(*_a):
        raise tokens.ShopeeVideoReconnectRequired(tokens.RECONNECT_MESSAGE)

    monkeypatch.setattr(tokens, "get_valid_authorization", reconnect)
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "failed" and "reconecte" in result.error
    assert FakeClient.instances == []


def test_not_configured_fails_clearly(monkeypatch, _base):
    def missing(*_a):
        raise tokens.ShopeeVideoNotConfigured("Conecte a conta Shopee Vídeo em Credenciais.")

    monkeypatch.setattr(tokens, "get_valid_authorization", missing)
    assert module.bot_post_shopee_video("job-1").status == "failed"


def test_products_without_external_id_publish_without_link_and_warn(monkeypatch, _base):
    monkeypatch.setattr(module.posts, "get_shopee_item_ids", lambda *a: [0, None])
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "succeeded"
    assert FakeClient.instances[0].info["product_item_ids"] == []
    assert "sem produto vinculado" in str(_meta(_base))


def test_caption_over_limit_fails_before_upload(monkeypatch, _base):
    monkeypatch.setattr(module.posts, "get", lambda *a: [{"text": "x" * 151, "medias": [VIDEO]}])
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "failed" and "150" in result.error
    assert FakeClient.instances == []


def test_upload_timeout_before_post_is_failed_not_unknown(_base):
    FakeClient.fail = {"wait_upload_result": sv.ShopeeVideoTimeout("prazo")}
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "failed"
    assert "post_video" not in FakeClient.instances[0].calls


def test_cover_failure_continues_without_cover(_base):
    FakeClient.fail = {"get_covers": sv.ShopeeVideoTransportError("rede")}
    assert module.bot_post_shopee_video("job-1").status == "succeeded"
    assert FakeClient.instances[0].info["cover_url"] is None


def test_network_error_after_post_reconciles_and_never_retries(_base):
    FakeClient.fail = {"post_video": sv.ShopeeVideoTransportError("timeout")}
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "unknown"
    assert FakeClient.instances[0].calls.count("post_video") == 1
    assert FakeClient.instances[0].calls[-1] == "find_posted_video"


def test_reconciliation_finds_posted_video(_base):
    FakeClient.fail = {"post_video": sv.ShopeeVideoTransportError("timeout")}
    FakeClient.found = {"video_upload_id": "upload-1", "video_id": "sv-found"}
    result = module.bot_post_shopee_video("job-1")
    assert (result.status, result.external_id) == ("succeeded", "sv-found")


def test_explicit_rejection_of_post_is_failed(_base):
    FakeClient.fail = {"post_video": sv.ShopeeVideoRejected("Shopee recusou a operação: error_param")}
    assert module.bot_post_shopee_video("job-1").status == "failed"


def test_reconciliation_failure_stays_unknown(_base):
    FakeClient.fail = {"post_video": sv.ShopeeVideoTransportError("timeout"),
                       "find_posted_video": sv.ShopeeVideoTransportError("rede")}
    assert module.bot_post_shopee_video("job-1").status == "unknown"


def test_metadata_rejection_is_failed(_base):
    FakeClient.fail = {"set_video_info": sv.ShopeeVideoRejected("Shopee recusou a operação: x")}
    result = module.bot_post_shopee_video("job-1")
    assert result.status == "failed" and "mark" not in FakeClient.instances[0].calls
