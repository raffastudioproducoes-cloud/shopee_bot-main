"""Prévia de campanha: contrato sem gravação e verificação de posse de lista."""
import asyncio
from datetime import date, time

import pytest

from api.routers import campaigns


def request(**changes):
    params = dict(
        list_id=11,
        item_ids=[12, 13],
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        weekdays=[1],
        start_time=time(9),
        end_time=time(10),
        posts_per_day=2,
    )
    params.update(changes)
    return campaigns.CampaignPreviewRequest(**params)


def test_list_must_be_exact_permutation():
    campaigns.validate_campaign_list_items([13, 12], [12, 13])
    with pytest.raises(ValueError, match="exatamente"):
        campaigns.validate_campaign_list_items([12, 999], [12, 13])
    with pytest.raises(ValueError, match="sem repetições"):
        campaigns.validate_campaign_list_items([12, 12], [12, 13])


def test_preview_is_read_only_and_uses_local_timezone(monkeypatch):
    reads = []
    monkeypatch.setattr(campaigns, "_get_list", lambda uid, lid, pid: (
        reads.append(("list", uid, lid, pid)) or {"id": lid, "name": "Minha lista"}
    ))
    monkeypatch.setattr(campaigns, "_get_list_products", lambda lid: (
        reads.append(("products", lid)) or [{"id": 12}, {"id": 13}]
    ))
    result = asyncio.run(campaigns.preview_campaign(request(), user_id=7, profile_id="p-7"))
    assert reads == [("list", 7, 11, "p-7"), ("products", 11)]
    assert result["slot_count"] == 2
    assert [slot["product_id"] for slot in result["slots"]] == [12, 13]
    assert result["slots"][0]["scheduled_utc"] == "2026-11-10T12:00:00+00:00"
    assert result["activated"] is False


def test_preview_rejects_forged_product_ids(monkeypatch):
    monkeypatch.setattr(campaigns, "_get_list", lambda *_: {"id": 11, "name": "Minha lista"})
    monkeypatch.setattr(campaigns, "_get_list_products", lambda *_: [{"id": 12}, {"id": 13}])
    with pytest.raises(campaigns.HTTPException) as error:
        asyncio.run(campaigns.preview_campaign(request(item_ids=[12, 999]), user_id=7, profile_id="p-7"))
    assert error.value.status_code == 422


def test_preview_rejects_more_than_fifteen_daily_posts():
    with pytest.raises(Exception):
        request(posts_per_day=16)
    with pytest.raises(Exception):
        request(posts_per_day=0)
