"""Rotina periódica de renovação Shopee Vídeo registrada no scheduler (a cada 2 h)."""

import inspect
import sys
import types

import shopee_bot.scheduler as scheduler


def test_init_registers_two_hour_refresh_job():
    source = inspect.getsource(scheduler.init)
    assert "_run_shopee_video_token_refresh" in source
    assert 'id="shopee_video_token_refresh"' in source
    assert scheduler.SHOPEE_VIDEO_REFRESH_HOURS == 2


def test_refresh_job_calls_tokens_and_never_raises(monkeypatch):
    calls = []
    fake = types.ModuleType("api.shopee_video_tokens")
    fake.refresh_expiring = lambda: calls.append(1) or {"refreshed": 1, "reconnect": 0, "errors": 0}
    monkeypatch.setitem(sys.modules, "api.shopee_video_tokens", fake)
    scheduler._run_shopee_video_token_refresh()
    assert calls == [1]

    def boom():
        raise RuntimeError("supabase fora")

    fake.refresh_expiring = boom
    scheduler._run_shopee_video_token_refresh()  # não propaga


def test_publisher_is_registered_everywhere():
    from shopee_bot.database.schedulers import NETWORK_FUNC_MAP
    from shopee_bot.scheduler import campaign_dispatch

    assert NETWORK_FUNC_MAP["shopee_video"] == "bot_post_shopee_video"
    assert "bot_post_shopee_video" in scheduler.PROFILE_SCOPED_FUNCS
    assert scheduler.NETWORK_BY_FUNC["bot_post_shopee_video"] == "shopee_video"
    assert campaign_dispatch.PUBLISHERS["shopee_video"] == "bot_post_shopee_video"
    assert callable(scheduler.bot_post_shopee_video)
