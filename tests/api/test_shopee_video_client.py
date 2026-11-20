"""Testes offline do cliente Shopee Vídeo; nunca chama Shopee de verdade."""

import hashlib
import hmac
import io
import pytest

from apis import shopee_video as sv


AUTH = sv.ShopeeVideoAuthorization(
    partner_id=123, partner_key="test-key-never-live",
    user_id=987, access_token="test-token-never-live",
    permission_granted=True,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def _next(self):
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self._next()

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self._next()


def _client(responses):
    fake = FakeSession(responses)
    return sv.ShopeeVideoClient(AUTH, enabled=True, session=fake), fake


def _user_sign(path, stamp=1700000000):
    message = f"123{path}{stamp}test-token-never-live987"
    return hmac.new(b"test-key-never-live", message.encode(), hashlib.sha256).hexdigest()


def test_permission_blocks_all_network_usage():
    fake = FakeSession([])
    with pytest.raises(sv.ShopeeVideoError, match="autorização"):
        sv.ShopeeVideoClient(AUTH, session=fake)
    with pytest.raises(sv.ShopeeVideoError, match="autorização"):
        sv.ShopeeVideoClient(sv.ShopeeVideoAuthorization(123, "k", 987, "t"), enabled=True, session=fake)
    assert fake.calls == []


def test_every_media_and_video_call_is_user_scoped(monkeypatch):
    monkeypatch.setattr(sv.time, "time", lambda: 1700000000)
    client, fake = _client([
        {"response": {"video_upload_id": "video-1", "part_size": 8}},
        {}, {},
        {"response": {"status": "SUCCEEDED"}},
        {"response": {"image_url_list": ["https://cf.shopee.test/c"]}},
        {"response": {"success_list": ["video-1"]}},
        {"response": {"success_list": [{"video_upload_id": "video-1", "post_id": "p1"}]}},
        {"response": {}}, {"response": {}}, {"response": {}}, {"response": {}}, {"response": {}},
    ])
    upload_id = client.upload_file(io.BytesIO(b"abcdefgh"), "v.mp4", 8, 15)
    client.wait_upload_result(upload_id, timeout_s=1, interval_s=0, sleep=lambda _s: None)
    client.get_covers(upload_id)
    client.set_video_info(upload_id, caption="Oi", cover_url=None, product_item_ids=[1], ai_assisted=False)
    client.post_video(upload_id)
    client.get_video_list()
    client.get_video_detail("vid-1")
    client.delete_video("vid-1")
    client.get_video_performance_list()
    client.get_video_detail_performance("vid-1")
    assert len(fake.calls) == 12
    for _method, url, kwargs in fake.calls:
        path = url.removeprefix(client.host)
        params = kwargs["params"]
        assert params["access_token"] == "test-token-never-live" and params["user_id"] == 987
        assert params["sign"] == _user_sign(path)
    assert fake.calls[0][2]["json"]["business"] == sv.INIT_UPLOAD_BUSINESS


def test_allowlist_blocks_unknown_paths():
    client, fake = _client([])
    with pytest.raises(sv.ShopeeVideoError, match="não autorizado"):
        client._request("/api/v2/shop/get_shop_info")
    assert fake.calls == []
    assert "/api/v2/video/delete_video" in sv.ALLOWED_PATHS
    assert "/api/v2/media/get_video_upload_result" in sv.ALLOWED_PATHS


def test_upload_chunks_names_and_md5():
    client, fake = _client([{}, {}, {}])
    client.upload_parts("video-1", io.BytesIO(b"abcdefgh"), 3, 8)
    assert [c[2]["data"]["part_seq"] for c in fake.calls] == [0, 1, 2]
    parts = [c[2]["files"]["part_content"] for c in fake.calls]
    assert [p[0] for p in parts] == ["video-1_part0.mp4", "video-1_part1.mp4", "video-1_part2.mp4"]
    assert [len(p[1]) for p in parts] == [3, 3, 2]
    assert all(c[2]["data"]["part_md5"] == hashlib.md5(p[1]).hexdigest() for c, p in zip(fake.calls, parts))


def test_wait_upload_result_polls_until_succeeded():
    client, fake = _client([
        {"response": {"status": "UPLOADING"}},
        {"response": {"status": "PROCESSING"}},
        {"response": {"status": "SUCCEEDED"}},
    ])
    assert client.wait_upload_result("video-1", timeout_s=60, interval_s=0, sleep=lambda _s: None) == "SUCCEEDED"
    assert len(fake.calls) == 3


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED"])
def test_wait_upload_result_failed_is_clear_error(status):
    client, _ = _client([{"response": {"status": status, "message": "token:never"}}])
    with pytest.raises(sv.ShopeeVideoError, match="processamento") as exc:
        client.wait_upload_result("video-1", timeout_s=60, interval_s=0, sleep=lambda _s: None)
    assert not isinstance(exc.value, sv.ShopeeVideoTimeout)


def test_wait_upload_result_timeout_is_distinguishable(monkeypatch):
    clock = iter([0, 0, 5, 11, 20])
    monkeypatch.setattr(sv.time, "monotonic", lambda: next(clock))
    client, _ = _client([{"response": {"status": "PROCESSING"}}] * 5)
    with pytest.raises(sv.ShopeeVideoTimeout):
        client.wait_upload_result("video-1", timeout_s=10, interval_s=0, sleep=lambda _s: None)


def test_post_requires_succeeded_upload_without_extra_get():
    client, fake = _client([{"response": {"success_list": [{"video_upload_id": "video-1", "post_id": "abc"}]}}])
    with pytest.raises(sv.ShopeeVideoError, match="processado"):
        client.post_video("video-1")
    assert fake.calls == []
    assert client.post_video("video-1", upload_status="SUCCEEDED")["confirmation"][0]["post_id"] == "abc"
    assert len(fake.calls) == 1 and fake.calls[0][1].endswith("/api/v2/video/post_video")


def test_reject_invalid_metadata_without_call():
    client, fake = _client([])
    base = {"cover_url": "https://example.test/1", "ai_assisted": True}
    with pytest.raises(sv.ShopeeVideoError, match="150"):
        client.set_video_info("video-1", caption="x" * 151, product_item_ids=[], **base)
    with pytest.raises(sv.ShopeeVideoError, match="150"):
        client.set_video_info("video-1", caption="   ", product_item_ids=[], **base)
    with pytest.raises(sv.ShopeeVideoError, match="seis"):
        client.set_video_info("video-1", caption="teste", product_item_ids=list(range(1, 8)), **base)
    with pytest.raises(sv.ShopeeVideoError, match="repita"):
        client.set_video_info("video-1", caption="teste", product_item_ids=[5, 5], **base)
    with pytest.raises(sv.ShopeeVideoError, match="IA"):
        client.set_video_info("video-1", caption="teste", product_item_ids=[], cover_url=None, ai_assisted="sim")
    assert fake.calls == []


def test_edit_info_includes_aigc_items_and_optional_cover():
    client, fake = _client([{"response": {"success_list": ["video-1"]}}] * 2)
    client.set_video_info(
        "video-1", caption="Produto legal", cover_url="https://example.test/cover",
        product_item_ids=[112233, 445566], ai_assisted=True,
    )
    body = fake.calls[0][2]["json"]
    assert body["aigc_label"] is True
    assert body["video_upload_list"][0]["item_info"] == [{"item_id": 112233}, {"item_id": 445566}]
    client.set_video_info("video-1", caption="Sem capa", cover_url=None, product_item_ids=[], ai_assisted=False)
    assert "cover_image_url" not in fake.calls[1][2]["json"]["video_upload_list"][0]


def test_find_posted_video_by_upload_id():
    client, _ = _client([{"response": {"video_list": [
        {"video_upload_id": "other", "video_id": "v0"},
        {"video_upload_id": "video-1", "video_id": "v1"},
    ]}}])
    assert client.find_posted_video("video-1")["video_id"] == "v1"


def test_get_video_list_sends_required_list_type():
    client, fake = _client([{"response": {"video_list": []}}])
    client.get_video_list()
    assert fake.calls[0][2]["params"]["list_type"] == 1


def test_get_video_list_rejects_unknown_list_type():
    client, _ = _client([])
    with pytest.raises(sv.ShopeeVideoError):
        client.get_video_list(list_type=3)


def test_find_posted_video_looks_in_both_lists():
    client, fake = _client([
        {"response": {"video_list": []}},
        {"response": {"video_list": [{"video_upload_id": "video-1", "video_id": "v1"}]}},
    ])
    assert client.find_posted_video("video-1")["video_id"] == "v1"
    assert [call[2]["params"]["list_type"] for call in fake.calls] == [1, 2]


def test_shopee_errors_dont_include_credentials_in_exception():
    client, _ = _client([{"error": "error_api_permission", "message": "token:test-token-never-live"}])
    with pytest.raises(sv.ShopeeVideoError) as exc:
        client.get_covers("video-1")
    assert "test-token-never-live" not in str(exc.value)


def test_network_failure_is_transport_error():
    import requests
    client, _ = _client([requests.ConnectionError("boom")])
    with pytest.raises(sv.ShopeeVideoTransportError):
        client.post_video("video-1", upload_status="SUCCEEDED")


def test_limits_for_brazil_shopee_video():
    client, fake = _client([{"response": {"video_upload_id": "v", "part_size": 8}}])
    with pytest.raises(sv.ShopeeVideoError, match="60 segundos"):
        client.init_upload("test.mp4", 800, 65)
    with pytest.raises(sv.ShopeeVideoError, match="MP4"):
        client.init_upload("test.mov", 800, 10)
    assert fake.calls == []
    client.init_upload("test.mp4", 800, None)
    assert "duration" not in fake.calls[0][2]["json"]
