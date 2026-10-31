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

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(self.responses.pop(0))

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(self.responses.pop(0))


def test_permission_blocks_all_network_usage():
    fake = FakeSession([])
    with pytest.raises(sv.ShopeeVideoError, match="autorização"):
        sv.ShopeeVideoClient(AUTH, session=fake)
    with pytest.raises(sv.ShopeeVideoError, match="autorização"):
        sv.ShopeeVideoClient(sv.ShopeeVideoAuthorization(123, "k", 987, "t"), enabled=True, session=fake)
    assert fake.calls == []


def test_public_signature_does_not_use_user_token(monkeypatch):
    monkeypatch.setattr(sv.time, "time", lambda: 1700000000)
    fake = FakeSession([{"response": {"video_upload_id": "video-1", "part_size": 3}}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    assert client.init_upload("test.mp4", 8, 15) == ("video-1", 3)
    params = fake.calls[0][2]["params"]
    message = "123/api/v2/media/init_video_upload1700000000"
    expected = hmac.new(b"test-key-never-live", message.encode(), hashlib.sha256).hexdigest()
    assert params == {"partner_id": 123, "timestamp": 1700000000, "sign": expected}
    assert fake.calls[0][2]["json"]["scene"] == 1


def test_user_scoped_signature(monkeypatch):
    monkeypatch.setattr(sv.time, "time", lambda: 1700000000)
    fake = FakeSession([{"response": {"image_url_list": ["https://example.test/cover"]}}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    assert client.get_covers("video-1") == ["https://example.test/cover"]
    params = fake.calls[0][2]["params"]
    message = "123/api/v2/video/get_cover_list1700000000test-token-never-live987"
    expected = hmac.new(b"test-key-never-live", message.encode(), hashlib.sha256).hexdigest()
    assert params["sign"] == expected
    assert params["user_id"] == 987


def test_upload_chunks_and_md5():
    fake = FakeSession([{}, {}, {}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    client.upload_parts("video-1", io.BytesIO(b"abcdefgh"), 3, 8)
    assert [c[2]["data"]["part_seq"] for c in fake.calls] == [0, 1, 2]
    assert [len(c[2]["files"]["part_content"][1]) for c in fake.calls] == [3, 3, 2]
    assert fake.calls[0][2]["data"]["part_md5"] == hashlib.md5(b"abc").hexdigest()


def test_reject_invalid_caption_and_many_products_without_call():
    fake = FakeSession([])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    with pytest.raises(sv.ShopeeVideoError, match="150"):
        client.set_video_info("video-1", caption="x" * 151,
                              cover_url="https://example.test/1", product_item_ids=[],
                              ai_assisted=True)
    with pytest.raises(sv.ShopeeVideoError, match="seis"):
        client.set_video_info("video-1", caption="teste",
                              cover_url="https://example.test/1",
                              product_item_ids=list(range(1, 8)), ai_assisted=True)
    assert fake.calls == []


def test_edit_info_includes_aigc_and_actual_item_ids():
    fake = FakeSession([{"response": {"success_list": ["video-1"]}}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    client.set_video_info(
        "video-1", caption="Produto legal", cover_url="https://example.test/cover",
        product_item_ids=[112233, 445566], ai_assisted=True,
    )
    body = fake.calls[0][2]["json"]
    assert body["aigc_label"] is True
    assert body["video_upload_list"][0]["item_info"] == [
        {"item_id": 112233}, {"item_id": 445566},
    ]


def test_post_requires_transcoding_and_server_confirmation():
    fake = FakeSession([{"response": {"status": "PROCESSING"}}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    with pytest.raises(sv.ShopeeVideoError, match="processado"):
        client.post_video("video-1")
    assert len(fake.calls) == 1

    fake2 = FakeSession([
        {"response": {"status": "SUCCEEDED"}},
        {"response": {"success_list": [{"video_upload_id": "video-1", "post_id": "abc"}]}},
    ])
    client2 = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake2)
    assert client2.post_video("video-1")["confirmation"][0]["post_id"] == "abc"


def test_shopee_errors_dont_include_credentials_in_exception():
    fake = FakeSession([{"error": "error_api_permission", "message": "token:test-token-never-live"}])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    with pytest.raises(sv.ShopeeVideoError) as exc:
        client.get_covers("video-1")
    assert "test-token-never-live" not in str(exc.value)


def test_limits_for_brazil_shopee_video():
    fake = FakeSession([])
    client = sv.ShopeeVideoClient(AUTH, enabled=True, session=fake)
    with pytest.raises(sv.ShopeeVideoError, match="60 segundos"):
        client.init_upload("test.mp4", 800, 65)
    assert fake.calls == []
