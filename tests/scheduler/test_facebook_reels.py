"""Reels do Facebook: fluxo oficial start -> upload -> finish -> status, com Graph simulada,
classificação failed/unknown, validação local do MP4 e limite de 30 por Página em 24 h."""

import struct
import sys

import pytest
import requests

from meta_fakes import FakeGraph, FakeResponse
import shopee_bot.apis.facebook as FacebookAPI
import shopee_bot.scheduler.bot_post_facebook  # noqa: F401
from shopee_bot.database.activity_types import ActivityType
from shopee_bot.scheduler import video_probe
from shopee_bot.utils import was_not_published

module = sys.modules["shopee_bot.scheduler.bot_post_facebook"]
BASE = FacebookAPI.API_BASE
REELS = f"{BASE}/page-1/video_reels"
UPLOAD = "https://rupload.facebook.com/video-upload/v26.0/vid-1"
STATUS = f"{BASE}/vid-1"
PUBLISHED = {"status": {"video_status": "ready", "publishing_phase": {"status": "complete", "publish_status": "published"}}}
PROCESSING = {"status": {"video_status": "processing", "publishing_phase": {"status": "not_started"}}}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(FacebookAPI.time, "sleep", lambda seconds: None)


class _ReelsGraph(FakeGraph):
    """Rotas do POST em /video_reels dependem da fase pedida."""

    def __init__(self, phases, status=(PUBLISHED,), upload=({"success": True},), start=None):
        super().__init__({("POST", UPLOAD): list(upload), ("GET", STATUS): list(status)})
        self.phases = {key: list(value) for key, value in phases.items()}
        self.start = start or {"video_id": "vid-1", "upload_url": UPLOAD}

    def post(self, url, params=None, data=None, json=None, timeout=None, headers=None, files=None):
        if url == REELS:
            self.calls.append({"method": "POST", "url": url, "params": params, "headers": headers})
            phase = params["upload_phase"]
            if phase == "start":
                return FakeResponse(self.start)
            queue = self.phases[phase]
            answer = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(answer, Exception):
                raise answer
            return answer if isinstance(answer, FakeResponse) else FakeResponse(answer)
        return super().post(url, params, data, json, timeout, headers, files)

    def phases_sent(self):
        return [c["params"]["upload_phase"] for c in self.calls if c["url"] == REELS]


def _install(monkeypatch, graph):
    monkeypatch.setattr(FacebookAPI.requests, "get", graph.get)
    monkeypatch.setattr(FacebookAPI.requests, "post", graph.post)
    return graph


def _post():
    return FacebookAPI.post_reel_as_page("page-tok", "page-1", "https://signed.example/v.mp4", "legenda #oferta")


def test_happy_path_follows_official_phases_and_returns_video_id(monkeypatch):
    graph = _install(monkeypatch, _ReelsGraph({"finish": [{"success": True}]}, status=(PROCESSING, PUBLISHED)))

    assert _post() == {"id": "vid-1"}
    assert graph.phases_sent() == ["start", "finish"]
    upload = next(c for c in graph.calls if c["url"] == UPLOAD)
    assert upload["headers"] == {"Authorization": "OAuth page-tok", "file_url": "https://signed.example/v.mp4"}
    finish = [c for c in graph.calls if c["url"] == REELS][1]["params"]
    assert finish["video_id"] == "vid-1" and finish["video_state"] == "PUBLISHED"
    assert finish["description"] == "legenda #oferta"


def test_finish_name_tolerates_complete_when_meta_refuses_finish(monkeypatch):
    graph = _install(monkeypatch, _ReelsGraph({
        "finish": [FakeResponse({"error": {"code": 100}}, status_code=400)],
        "complete": [{"success": True}],
    }))
    assert _post() == {"id": "vid-1"}
    assert graph.phases_sent() == ["start", "finish", "complete"]


@pytest.mark.parametrize("graph_kwargs", [
    {"start": {"error": {"code": 200}}},  # start recusado
    {"upload": (FakeResponse({"success": False}, status_code=500),)},  # upload falhou
    {"start": {"video_id": "vid-1", "upload_url": "https://evil.example/up"}},  # host inesperado
])
def test_failures_before_finish_are_not_published(monkeypatch, graph_kwargs):
    graph = _install(monkeypatch, _ReelsGraph({"finish": [{"success": True}]}, **graph_kwargs))
    with pytest.raises(Exception) as err:
        _post()
    assert was_not_published(err.value)
    assert "finish" not in graph.phases_sent()
    assert all(c["url"] != "https://evil.example/up" for c in graph.calls)  # token nunca vai a outro host


def test_finish_refused_by_meta_is_failed(monkeypatch):
    _install(monkeypatch, _ReelsGraph({"finish": [FakeResponse({"error": {"code": 200}}, status_code=403)]}))
    with pytest.raises(Exception) as err:
        _post()
    assert was_not_published(err.value)


def test_finish_response_lost_is_unknown_without_token_in_message(monkeypatch):
    _install(monkeypatch, _ReelsGraph({"finish": [requests.exceptions.ReadTimeout("url?access_token=page-tok")]}))
    with pytest.raises(Exception) as err:
        _post()
    assert not was_not_published(err.value)
    assert "page-tok" not in str(err.value)


def test_processing_error_after_finish_is_failed(monkeypatch):
    error = {"status": {"video_status": "error", "processing_phase": {"status": "error"}}}
    _install(monkeypatch, _ReelsGraph({"finish": [{"success": True}]}, status=(error,)))
    with pytest.raises(Exception) as err:
        _post()
    assert was_not_published(err.value)


def test_confirmation_timeout_is_unknown(monkeypatch):
    clock = iter(range(0, 10_000, 100))
    monkeypatch.setattr(FacebookAPI.time, "monotonic", lambda: next(clock))
    graph = _install(monkeypatch, _ReelsGraph({"finish": [{"success": True}]}, status=(PROCESSING,)))
    with pytest.raises(Exception, match="5 min") as err:
        _post()
    assert not was_not_published(err.value)
    assert len(graph.urls("GET")) < 10  # respeita o limite de ~5 min


@pytest.mark.parametrize("name,info,expected", [
    ("v.mov", None, "MP4"),
    ("v.mp4", {"width": 1080, "height": 1920, "duration": 2.5}, "3 a 90 s"),
    ("v.mp4", {"width": 1080, "height": 1920, "duration": 91}, "3 a 90 s"),
    ("v.mp4", {"width": 1920, "height": 1080, "duration": 30}, "vertical"),
    ("v.mp4", {"width": 480, "height": 854, "duration": 30}, "540×960"),
    ("v.mp4", {"width": 1080, "height": 1920, "duration": 30}, None),
    ("v.mp4", {"width": 1080, "height": 1350, "duration": 30}, None),  # vertical, só aviso
    ("v.mp4", None, None),  # ilegível: a Meta valida
])
def test_reel_requirements(name, info, expected):
    problem = FacebookAPI.reel_requirements_error(name, info)
    assert (problem is None) if expected is None else (expected in problem)


def test_aspect_warning_only_outside_nine_by_sixteen():
    assert FacebookAPI.reel_aspect_warning({"width": 1080, "height": 1920, "duration": 5}) is None
    assert "9:16" in FacebookAPI.reel_aspect_warning({"width": 1080, "height": 1350, "duration": 5})


# --- leitura do MP4 por Range ---------------------------------------------

def _box(kind, body):
    return struct.pack(">I4s", 8 + len(body), kind) + body


def _mp4(width, height, seconds, rotated=False, moov_last=True):
    mvhd = bytes(12) + struct.pack(">II", 1000, int(seconds * 1000)) + bytes(80)
    matrix = (0, 0x10000, 0, -0x10000, 0, 0, 0, 0, 0x40000000) if rotated else (0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    tkhd = bytes(40) + struct.pack(">9i", *matrix) + struct.pack(">II", width << 16, height << 16)
    hdlr = bytes(8) + b"vide" + bytes(12)
    moov = _box(b"moov", _box(b"mvhd", mvhd) + _box(b"trak", _box(b"tkhd", tkhd) + _box(b"mdia", _box(b"hdlr", hdlr))))
    ftyp = _box(b"ftyp", b"isom" + bytes(4))
    mdat = _box(b"mdat", bytes(5000))
    return ftyp + (mdat + moov if moov_last else moov + mdat)


class _RangeServer:
    def __init__(self, blob, honor_range=True):
        self.blob, self.honor, self.requested = blob, honor_range, 0

    def get(self, url, headers=None, stream=False, timeout=None):
        start, end = (int(x) for x in headers["Range"].split("=")[1].split("-"))
        self.requested += end - start + 1
        server = self

        class _Raw:
            def read(self, n):
                return server.blob[start:end + 1][:n]

        class _Res:
            status_code = 206 if server.honor else 200
            raw = _Raw()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return _Res()


@pytest.mark.parametrize("moov_last", [True, False])
def test_probe_reads_dimensions_and_duration_without_mdat(monkeypatch, moov_last):
    server = _RangeServer(_mp4(1080, 1920, 12.5, moov_last=moov_last))
    monkeypatch.setattr(video_probe.requests, "get", server.get)
    assert video_probe.probe_mp4("https://signed.example/v.mp4") == {"width": 1080, "height": 1920, "duration": 12.5}
    assert server.requested < 1000  # nunca baixa o mdat de 5 kB


def test_probe_applies_90_degree_rotation(monkeypatch):
    monkeypatch.setattr(video_probe.requests, "get", _RangeServer(_mp4(1920, 1080, 8, rotated=True)).get)
    info = video_probe.probe_mp4("https://signed.example/v.mp4")
    assert (info["width"], info["height"]) == (1080, 1920)


@pytest.mark.parametrize("server", [
    _RangeServer(_mp4(1080, 1920, 5), honor_range=False),  # sem Range: não baixa tudo
    _RangeServer(b"not an mp4 file at all........"),
])
def test_probe_returns_none_when_unreadable(monkeypatch, server):
    monkeypatch.setattr(video_probe.requests, "get", server.get)
    assert video_probe.probe_mp4("https://signed.example/v.mp4") is None


# --- publicador (scheduler) -----------------------------------------------

VIDEO = {"type": "VIDEO", "file_name": "v.mp4", "file_path": "storage://post-media/v.mp4"}


def _scheduler(monkeypatch, reels=True, info=None, used=0, reel=None):
    monkeypatch.setattr(module.schedulers, "get_by_id",
                        lambda job_id: {"user_id": 42, "post_id": 7, "profile_id": "profile-1"})
    monkeypatch.setattr(module.facebook_credentials, "get_by_user_id", lambda *a, **k: {
        "username": "fulano", "facebook_app_id": None, "facebook_secret": None,
        "facebook_page_id": "page-1", "facebook_page_access_token": "page-tok"})
    monkeypatch.setattr(module.posts, "get",
                        lambda *a: [{"text": "clipe", "product_ids": [], "medias": [VIDEO]}])
    monkeypatch.setattr(module.posts, "get_facebook_reels", lambda *a: reels)
    monkeypatch.setattr(module.posts, "count_facebook_reels_last_24h", lambda page_id: used)
    monkeypatch.setattr(module, "delivery_url", lambda media: ("https://signed.example/v.mp4", lambda: None))
    monkeypatch.setattr(module, "probe_mp4", lambda url: info)
    calls = {"reel": [], "video": []}
    monkeypatch.setattr(module.FacebookAPI, "post_reel_as_page",
                        reel or (lambda *a: calls["reel"].append(a) or {"id": "vid-1"}))
    monkeypatch.setattr(module.FacebookAPI, "post_video_as_page",
                        lambda *a: calls["video"].append(a) or {"id": "vid-2"})
    activities = []
    monkeypatch.setattr(module, "insert_activities",
                        lambda user_id, kind, metadata, profile_id=None: activities.append((kind, metadata)))
    return calls, activities


GOOD = {"width": 1080, "height": 1920, "duration": 20}


def test_scheduler_publishes_reel_when_chosen(monkeypatch):
    calls, activities = _scheduler(monkeypatch, info=GOOD)
    result = module.bot_post_facebook("job-reel")
    assert result.status == "succeeded" and result.external_id == "vid-1"
    assert calls["reel"] == [("page-tok", "page-1", "https://signed.example/v.mp4", "clipe")] and not calls["video"]
    assert activities[0][0] == ActivityType.BOT_POST_SUCCESS


def test_old_post_without_choice_keeps_regular_video(monkeypatch):
    calls, _ = _scheduler(monkeypatch, reels=False, info=GOOD)
    assert module.bot_post_facebook("job-old").status == "succeeded"
    assert calls["video"] and not calls["reel"]


def test_invalid_video_fails_before_any_meta_call(monkeypatch):
    calls, activities = _scheduler(monkeypatch, info={"width": 1920, "height": 1080, "duration": 20})
    result = module.bot_post_facebook("job-wide")
    assert result.status == "failed" and "vertical" in result.error
    assert not calls["reel"] and not calls["video"]
    assert activities[0][0] == ActivityType.BOT_POST_FAILURE


def test_thirty_reels_per_page_in_24h_blocks_locally(monkeypatch):
    calls, _ = _scheduler(monkeypatch, info=GOOD, used=30)
    result = module.bot_post_facebook("job-limit")
    assert result.status == "failed" and "30 Reels" in result.error
    assert not calls["reel"]


def test_lost_finish_response_becomes_unknown(monkeypatch):
    def lost(*a):
        raise Exception("Facebook Reels: a resposta da publicação se perdeu")
    _scheduler(monkeypatch, info=GOOD, reel=lost)
    assert module.bot_post_facebook("job-lost").status == "unknown"


def test_reels_flag_sql_reads_head_choice_then_campaign_item_and_defaults_off():
    from shopee_bot.database import posts as posts_db
    sql = posts_db.FACEBOOK_REELS_SQL
    assert "p.tiktok_options->'reels'" in sql and "p.network = 'facebook'" in sql
    assert "i->'facebook_reels'" in sql and "s.network = 'facebook'" in sql
    assert sql.rstrip().endswith("false)")  # sem escolha = vídeo comum
    seen = {}
    original = posts_db.query_db
    try:
        posts_db.query_db = lambda q, args, one=False: seen.update(q=q, args=args) or {"total": 4}
        assert posts_db.count_facebook_reels_last_24h("page-1") == 4
    finally:
        posts_db.query_db = original
    assert seen["args"] == ("page-1",) and "interval '24 hours'" in seen["q"]
