from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api import campaign_activation


@pytest.mark.asyncio
async def test_shopee_image_is_sanitized_once_and_network_size_limit_uses_real_bytes(monkeypatch):
    content = b"source-image"
    normalized = SimpleNamespace(
        content=b"x" * (4 * 1024 * 1024 + 1),
        mime_type="image/jpeg",
    )
    monkeypatch.setattr(campaign_activation, "_download_shopee_image", AsyncMock(return_value=content))
    monkeypatch.setattr(
        campaign_activation, "detect_media_type",
        lambda _content: SimpleNamespace(media_type="IMAGE", mime_type="image/jpeg", extension=".jpg"),
    )
    monkeypatch.setattr(campaign_activation, "sanitize_media_upload", lambda *_args, **_kwargs: normalized)
    monkeypatch.setattr(campaign_activation, "_normalize_shopee_photo_as_jpeg", lambda media, _product: media)

    sources = [{
        "source_id": "shopee:12",
        "product_id": 12,
        "file_name": "shopee-12.jpg",
        "type": "IMAGE",
        "size": 0,
        "source_image": "https://images.example.invalid/product.jpg",
        "from_shopee": True,
    }]
    await campaign_activation._prepare_shopee_sources(sources)

    assert sources[0]["size"] == 4 * 1024 * 1024 + 1
    assert sources[0]["prepared_media"] is normalized
    campaign_activation._download_shopee_image.assert_awaited_once_with(
        "https://images.example.invalid/product.jpg"
    )

    reservation = {
        "draft_snapshot": {
            "items": [{
                "product_id": 12,
                "networks": ["facebook"],
                "copy": "Descrição",
                "network_copies": {},
                "affiliate_link": "",
            }],
        },
        "media_snapshot": [],
    }
    _, compatible, networks = campaign_activation._validate_plans(reservation, sources)

    assert networks == {"facebook"}
    # Facebook aceita no máximo 4 MiB por imagem; a foto fica fora
    # somente dessa composição, sem alterar o arquivo original.
    assert compatible["shopee:12"] == set()
