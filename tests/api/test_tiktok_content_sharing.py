"""Content Sharing Guidelines do TikTok: escolhas explícitas do usuário,
creator_info sem expor token e recusa de criar/agendar/ativar sem consentimento.
Nenhuma chamada real ao TikTok: tudo mockado."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import tiktok_creator, tiktok_oauth
from api.crypto import decrypt, encrypt
from api.main import app
from api.routers import credentials as credentials_module
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.campaigns import CampaignDraftItem, _require_tiktok_choices
from api.routers.profiles import get_current_profile_id
from api.tiktok_options import (
    RECONFIRM_MESSAGE, TikTokPostOptions, check_against_creator, direct_post_info,
    parse_stored, require_campaign_choices, stored_options,
)

SCHEDULE = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}
DIRECT = {"mode": "direct", "privacy_level": "SELF_ONLY", "consent": True}
CREATOR = {
    "creator_nickname": "Loja da Ana", "creator_username": "lojadaana",
    "creator_avatar_url": "https://p16.tiktokcdn.test/a.jpg",
    "privacy_level_options": ["FOLLOWER_OF_CREATOR", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
    "comment_disabled": False, "duet_disabled": True, "stitch_disabled": True,
    "max_video_post_duration_sec": 600,
}


# ── regras da guideline (sem rede) ──────────────────────────────────────────

@pytest.mark.parametrize("data, message", [
    ({"mode": "direct", "privacy_level": "SELF_ONLY"}, "Confirme a declaração"),
    ({"mode": "direct", "consent": True}, "Escolha quem pode ver"),
    ({**DIRECT, "commercial_content": True}, "promove você, um terceiro ou ambos"),
    ({**DIRECT, "brand_content": True}, "Ative 'Divulgar conteúdo comercial'"),
    ({**DIRECT, "commercial_content": True, "brand_content": True}, "não pode ser privada"),
    ({"mode": "draft", "consent": True, "privacy_level": "SELF_ONLY"}, "app do TikTok"),
    ({**DIRECT, "privacy_level": "PUBLIC"}, ""),
])
def test_guideline_rules_reject_invalid_choices(data, message):
    with pytest.raises(ValueError, match=message):
        TikTokPostOptions.model_validate(data)


def test_valid_choices_and_no_default_privacy():
    assert TikTokPostOptions.model_validate({"mode": "draft", "consent": True}).privacy_level is None
    both = TikTokPostOptions.model_validate({
        **DIRECT, "privacy_level": "MUTUAL_FOLLOW_FRIENDS", "commercial_content": True,
        "brand_organic": True, "brand_content": True,
    })
    assert both.brand_content and both.brand_organic
    # Sua marca sozinha pode ser privada (só Conteúdo de marca não pode).
    TikTokPostOptions.model_validate({**DIRECT, "commercial_content": True, "brand_organic": True})


def test_unchecked_interactions_mean_disabled_and_creator_restriction_wins():
    options = TikTokPostOptions.model_validate({**DIRECT, "allow_comment": True})
    info = direct_post_info(options, "legenda", {**CREATOR, "comment_disabled": False})
    assert info == {
        "title": "legenda", "privacy_level": "SELF_ONLY",
        "disable_comment": False, "disable_duet": True, "disable_stitch": True,
        "brand_content_toggle": False, "brand_organic_toggle": False, "is_aigc": False,
    }
    assert direct_post_info(options, "", {**CREATOR, "comment_disabled": True})["disable_comment"] is True


def test_check_against_creator():
    check_against_creator(TikTokPostOptions.model_validate(DIRECT), CREATOR)
    with pytest.raises(ValueError, match="privacidade"):
        check_against_creator(TikTokPostOptions.model_validate(
            {**DIRECT, "privacy_level": "PUBLIC_TO_EVERYONE"}), CREATOR)
    with pytest.raises(ValueError, match="Duet"):
        check_against_creator(TikTokPostOptions.model_validate({**DIRECT, "allow_duet": True}), CREATOR)


def test_stored_options_roundtrip_and_legacy_rows_need_reconfirmation():
    saved = stored_options(TikTokPostOptions.model_validate(DIRECT))
    assert saved["confirmed_at"] and saved["privacy_level"] == "SELF_ONLY"
    assert parse_stored(saved).privacy_level == "SELF_ONLY"
    for raw in (None, {}, {"mode": "direct"}, "SELF_ONLY", {**DIRECT, "extra": 1}):
        with pytest.raises(ValueError, match="Reconfirme as opções do TikTok"):
            parse_stored(raw)


def test_campaign_items_with_tiktok_require_choices():
    require_campaign_choices([{"networks": ["threads"]}])
    require_campaign_choices([{"networks": ["tiktok"], "tiktok": stored_options(
        TikTokPostOptions.model_validate(DIRECT))}])
    with pytest.raises(ValueError, match=RECONFIRM_MESSAGE[:20]):
        require_campaign_choices([{"networks": ["tiktok"]}])
    item = CampaignDraftItem.model_validate({"product_id": 1, "title": "t", "copy": "c", "networks": ["tiktok"]})
    with pytest.raises(ValueError, match="incluir o TikTok na campanha"):
        _require_tiktok_choices([item])


# ── criação/agendamento de posts ────────────────────────────────────────────

@pytest.fixture
def api(fake_db, monkeypatch):
    db = fake_db({"posts": [], "medias": [], "posts_medias": [], "posts_products": [], "products": []})
    monkeypatch.setattr(posts_module, "supabase", db)
    checked = []

    async def allowed(options, user_id, profile_id):
        checked.append((options, user_id, profile_id))

    async def fake_job(**_kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "require_allowed_choice", allowed)
    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    monkeypatch.setattr(posts_module, "_preview_batch", lambda body, drafts, x=True: [
        {"network": c.network, "texts": c.texts[:1], "mode": "single_media", "media_draft_ids": [],
         "warnings": [], "blocked_reason": None, "dropped": []} for c in body.compositions
    ])
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app), db, checked, monkeypatch
    app.dependency_overrides.clear()


def _batch(compositions):
    return {"compositions": compositions, "schedule": SCHEDULE}


def test_batch_without_tiktok_choices_is_422_and_creates_nothing(api):
    client, db, _checked, _mp = api
    res = client.post("/posts/batch", json=_batch([
        {"network": "threads", "texts": ["oi"]}, {"network": "tiktok", "texts": ["oi"]},
    ]))
    assert res.status_code == 422
    assert "TikTok" in res.text and "declaração" in res.text
    assert db.tables["posts"] == []


def test_branded_content_private_is_rejected_by_backend(api):
    client, db, _checked, _mp = api
    res = client.post("/posts/batch", json=_batch([{"network": "tiktok", "texts": ["oi"], "tiktok": {
        **DIRECT, "commercial_content": True, "brand_content": True}}]))
    assert res.status_code == 422
    assert "não pode ser privada" in res.text
    assert db.tables["posts"] == []


def test_tiktok_options_on_other_network_rejected(api):
    client, _db, _checked, _mp = api
    res = client.post("/posts/batch", json=_batch([{"network": "threads", "texts": ["oi"], "tiktok": DIRECT}]))
    assert res.status_code == 422


def test_batch_stores_exact_choice_only_on_tiktok_post(api):
    client, db, checked, _mp = api
    choice = {**DIRECT, "privacy_level": "MUTUAL_FOLLOW_FRIENDS", "allow_comment": True,
              "commercial_content": True, "brand_organic": True}
    res = client.post("/posts/batch", json=_batch([
        {"network": "threads", "texts": ["oi"]}, {"network": "tiktok", "texts": ["legenda"], "tiktok": choice},
    ]))
    assert res.status_code == 201, res.text
    heads = {row["network"]: row for row in db.tables["posts"]}
    assert "tiktok_options" not in heads["threads"]
    stored = heads["tiktok"]["tiktok_options"]
    assert stored["privacy_level"] == "MUTUAL_FOLLOW_FRIENDS" and stored["allow_comment"] is True
    assert stored["brand_organic"] is True and stored["brand_content"] is False
    assert stored["consent"] is True and stored["confirmed_at"]
    assert checked and checked[0][1:] == (42, "profile-a")


def test_creator_refusal_blocks_only_tiktok(api):
    client, db, _checked, mp = api

    async def refuse(options, user_id, profile_id):
        raise HTTPException(status_code=422, detail="A privacidade escolhida não está disponível")

    mp.setattr(posts_module, "require_allowed_choice", refuse)
    res = client.post("/posts/batch", json=_batch([
        {"network": "threads", "texts": ["oi"]}, {"network": "tiktok", "texts": ["oi"], "tiktok": DIRECT},
    ]))
    assert res.status_code == 201
    body = res.json()
    assert [c["network"] for c in body["created"]] == ["threads"]
    assert body["blocked"][0]["network"] == "tiktok"
    assert "privacidade" in body["blocked"][0]["blocked_reason"]
    assert {row["network"] for row in db.tables["posts"]} == {"threads"}


def test_draft_mode_is_accepted_and_stored(api):
    client, db, _checked, _mp = api
    res = client.post("/posts/batch", json=_batch([
        {"network": "tiktok", "texts": ["oi"], "tiktok": {"mode": "draft", "consent": True}},
    ]))
    assert res.status_code == 201, res.text
    assert db.tables["posts"][0]["tiktok_options"]["mode"] == "draft"


# ── GET /credentials/tiktok/creator-info ───────────────────────────────────

@pytest.fixture
def creator_api(fake_db, monkeypatch):
    db = fake_db({"tiktok_credentials": [{
        "id": 1, "user_id": 42, "profile_id": "profile-a",
        "user_access_token": encrypt("old-access"), "refresh_token": encrypt("refresh-1"),
    }]})
    monkeypatch.setattr(tiktok_creator, "supabase", db)
    monkeypatch.setattr(credentials_module, "_creator_info_attempts", {})
    monkeypatch.setattr(tiktok_oauth, "CLIENT_KEY", "ck")
    monkeypatch.setattr(tiktok_oauth, "CLIENT_SECRET", "cs")
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app), db, monkeypatch
    app.dependency_overrides.clear()


def _query(responses, seen):
    async def query(token):
        seen.append(token)
        return responses.pop(0)
    return query


def test_creator_info_maps_public_fields_without_tokens(creator_api):
    client, _db, mp = creator_api
    seen = []
    mp.setattr(tiktok_oauth, "query_creator_info", _query([("ok", CREATOR)], seen))
    res = client.get("/credentials/tiktok/creator-info")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["creator_nickname"] == "Loja da Ana"
    assert body["privacy_level_options"] == CREATOR["privacy_level_options"]
    assert body["duet_disabled"] is True and body["comment_disabled"] is False
    assert body["max_video_post_duration_sec"] == 600 and body["can_post"] is True
    assert "old-access" not in res.text and "refresh-1" not in res.text and "token" not in res.text
    assert seen == ["old-access"]


def test_creator_info_refreshes_expired_token_once_and_persists_encrypted(creator_api):
    client, db, mp = creator_api
    seen = []
    mp.setattr(tiktok_oauth, "query_creator_info",
               _query([("access_token_invalid", {}), ("ok", CREATOR)], seen))

    async def refresh(token):
        assert token == "refresh-1"
        return {"access_token": "new-access", "refresh_token": "refresh-2"}

    mp.setattr(tiktok_oauth, "refresh_access_token", refresh)
    res = client.get("/credentials/tiktok/creator-info")
    assert res.status_code == 200
    assert seen == ["old-access", "new-access"]
    row = db.tables["tiktok_credentials"][0]
    assert decrypt(row["user_access_token"]) == "new-access"
    assert decrypt(row["refresh_token"]) == "refresh-2"


def test_creator_info_cannot_post_is_shown_not_hidden(creator_api):
    client, _db, mp = creator_api
    mp.setattr(tiktok_oauth, "query_creator_info", _query([("spam_risk_too_many_posts", CREATOR)], []))
    body = client.get("/credentials/tiktok/creator-info").json()
    assert body["can_post"] is False and "limite diário" in body["cannot_post_reason"]


def test_creator_info_requires_connection_of_this_profile(creator_api):
    client, _db, _mp = creator_api
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-b"
    res = client.get("/credentials/tiktok/creator-info")
    assert res.status_code == 409
    assert "Conecte o TikTok" in res.json()["detail"]


def test_creator_info_is_rate_limited(creator_api):
    client, _db, mp = creator_api

    async def query(token):
        return "ok", CREATOR

    mp.setattr(tiktok_oauth, "query_creator_info", query)
    codes = [client.get("/credentials/tiktok/creator-info").status_code for _ in range(16)]
    assert codes[:15] == [200] * 15 and codes[15] == 429


@pytest.mark.anyio
async def test_require_allowed_choice_uses_live_creator_info(monkeypatch):
    async def creator(user_id, profile_id):
        return {**tiktok_creator.public_creator_info(CREATOR)}

    monkeypatch.setattr(tiktok_creator, "load_creator_info", creator)
    await tiktok_creator.require_allowed_choice(TikTokPostOptions.model_validate(DIRECT), 42, "p")
    with pytest.raises(HTTPException) as err:
        await tiktok_creator.require_allowed_choice(TikTokPostOptions.model_validate(
            {**DIRECT, "privacy_level": "PUBLIC_TO_EVERYONE"}), 42, "p")
    assert err.value.status_code == 422

    async def blocked(user_id, profile_id):
        return tiktok_creator.public_creator_info(CREATOR, "reached_active_user_cap")

    monkeypatch.setattr(tiktok_creator, "load_creator_info", blocked)
    with pytest.raises(HTTPException) as err:
        await tiktok_creator.require_allowed_choice(TikTokPostOptions.model_validate(DIRECT), 42, "p")
    assert err.value.status_code == 409
    # Rascunho não depende de privacidade: não consulta creator_info.
    await tiktok_creator.require_allowed_choice(
        TikTokPostOptions.model_validate({"mode": "draft", "consent": True}), 42, "p")


# ── campanhas: salvar/ativar exige as mesmas escolhas ───────────────────────

def _campaign_payload(tiktok):
    from api.routers import campaigns
    item = {"product_id": 12, "title": "Produto", "copy": "", "affiliate_link": "",
            "networks": ["tiktok"], "network_copies": {}, "use_shopee_image": False}
    if tiktok is not None:
        item["tiktok"] = tiktok
    return campaigns.CampaignDraftSave(name="Novembro", list_id=11, items=[item], schedule=None)


def _campaign_env(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from api.routers import campaigns
    from api.campaign_policy import CampaignPolicy

    writes = []

    class _Query:
        def insert(self, row):
            writes.append(row)
            return self

        def execute(self):
            return SimpleNamespace(data=[{**writes[-1], "id": "draft-1", "revision": 1}])

    monkeypatch.setattr(campaigns, "load_campaign_policy", lambda *_: CampaignPolicy("premium", False, 5, 30, 15, True))
    monkeypatch.setattr(campaigns, "_get_list", lambda uid, lid, pid: {"id": lid, "name": "Lista"})
    monkeypatch.setattr(campaigns, "_get_list_products", lambda lid: [{"id": 12, "image": None}])
    monkeypatch.setattr(campaigns, "supabase", SimpleNamespace(table=lambda name: _Query()), raising=False)
    return asyncio, campaigns, writes


def test_campaign_draft_with_tiktok_without_choices_is_422(monkeypatch):
    asyncio, campaigns, writes = _campaign_env(monkeypatch)
    with pytest.raises(HTTPException) as err:
        asyncio.run(campaigns.create_campaign_draft(_campaign_payload(None), user_id=42, profile_id="p"))
    assert err.value.status_code == 422 and "TikTok" in err.value.detail
    assert writes == []


def test_campaign_draft_stores_confirmed_tiktok_choice(monkeypatch):
    asyncio, campaigns, writes = _campaign_env(monkeypatch)
    asyncio.run(campaigns.create_campaign_draft(_campaign_payload(DIRECT), user_id=42, profile_id="p"))
    stored = writes[0]["items"][0]["tiktok"]
    assert stored["privacy_level"] == "SELF_ONLY" and stored["consent"] is True and stored["confirmed_at"]


def test_activation_of_legacy_campaign_without_choices_fails_before_reserving(monkeypatch):
    import asyncio
    from api import campaign_activation
    from api.routers import campaigns

    monkeypatch.setattr(campaign_activation, "load_campaign_policy", lambda *_: object())
    monkeypatch.setattr(campaign_activation, "require_campaign_access", lambda policy: None)
    monkeypatch.setattr(campaigns, "_get_owned_campaign", lambda *a: {
        "status": "draft", "revision": 3, "source_list_id": 11,
        "schedule": {"list_id": 11, "item_ids": [12], "start_date": "2099-01-05", "end_date": "2099-01-06",
                     "weekdays": [0], "start_time": "09:00", "end_time": "10:00", "posts_per_day": 1},
        "items": [{"product_id": 12, "title": "t", "copy": "c", "networks": ["tiktok"]}],
    })
    monkeypatch.setattr(campaign_activation, "_rpc", lambda *a: pytest.fail("não deve reservar"))
    with pytest.raises(HTTPException) as err:
        asyncio.run(campaign_activation.activate("d", 3, 42, "p"))
    assert err.value.status_code == 422
    assert err.value.detail == RECONFIRM_MESSAGE
