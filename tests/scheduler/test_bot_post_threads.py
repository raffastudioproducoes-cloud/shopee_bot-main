"""bot_post (Threads) publica mídia durável via URL assinada do Supabase Storage."""

import sys

import shopee_bot.scheduler.bot_post  # noqa: F401
from shopee_bot.scheduler import media_delivery
from tests.scheduler.meta_fakes import FakeStorage

module = sys.modules["shopee_bot.scheduler.bot_post"]


def _setup(monkeypatch, medias):
    storage = FakeStorage()
    monkeypatch.setattr(media_delivery, "_storage", lambda: storage)
    monkeypatch.setattr(module.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(module.threads_credentials, "get_by_user_id",
                        lambda u, p: {"username": "u", "threads_user_id": "tu", "threads_access_token": "tok"})
    monkeypatch.setattr(module.posts, "get",
                        lambda u, post, p: [{"text": "oi", "medias": medias}])
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)
    return storage


def _durable(name, kind="IMAGE"):
    return {"type": kind, "file_path": f"storage://bucket/{name}", "file_name": name}


def test_imagem_duravel_usa_url_assinada_sem_checar_disco(monkeypatch):
    storage = _setup(monkeypatch, [_durable("a.jpg")])
    sent = {}
    monkeypatch.setattr(module.ThreadsAPI, "make_post",
                        lambda *a, **k: sent.update(args=a, kw=k) or "t1")
    module.bot_post("j")
    assert storage.signed == [("bucket", "a.jpg", media_delivery.SIGNED_URL_TTL)]
    assert sent["kw"]["media_type"] == "IMAGE"
    assert sent["kw"]["image_url"].startswith("https://signed.example/bucket/a.jpg")


def test_video_duravel(monkeypatch):
    _setup(monkeypatch, [_durable("v.mp4", "VIDEO")])
    sent = {}
    monkeypatch.setattr(module.ThreadsAPI, "make_post", lambda *a, **k: sent.update(kw=k) or "t1")
    module.bot_post("j")
    assert sent["kw"]["media_type"] == "VIDEO"
    assert sent["kw"]["video_url"].startswith("https://signed.example/bucket/v.mp4")


def test_carrossel_duravel(monkeypatch):
    storage = _setup(monkeypatch, [_durable("a.jpg"), _durable("v.mp4", "VIDEO")])
    sent = {}
    monkeypatch.setattr(module.ThreadsAPI, "make_carousel_post",
                        lambda uid, tok, text, medias, reply=None: sent.update(m=medias) or "t1")
    module.bot_post("j")
    assert [m["type"] for m in sent["m"]] == ["IMAGE", "VIDEO"]
    assert all(m["url"].startswith("https://signed.example/") for m in sent["m"])
    assert len(storage.signed) == 2


def test_midia_legada_existente_e_rejeitada_sem_servico_externo(monkeypatch, tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    _setup(monkeypatch, [{"type": "IMAGE", "file_path": str(f), "file_name": "a.jpg"}])
    acts = []
    monkeypatch.setattr(module, "insert_activities", lambda u, t, m, profile_id=None: acts.append(m))
    monkeypatch.setattr(module.ThreadsAPI, "make_post", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("não deve chamar a rede para mídia legada")
    ))
    module.bot_post("j")
    assert "Reenvie" in str(acts[0])


def test_midia_legada_ausente_falha_com_mensagem(monkeypatch):
    _setup(monkeypatch, [{"type": "IMAGE", "file_path": "C:/nao/existe.jpg", "file_name": "e.jpg"}])
    acts = []
    monkeypatch.setattr(module, "insert_activities", lambda u, t, m, profile_id=None: acts.append(m))
    monkeypatch.setattr(module.ThreadsAPI, "make_post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria publicar")))
    module.bot_post("j")
    assert "não encontrado" in str(acts[0])


def test_texto_inalterado(monkeypatch):
    _setup(monkeypatch, [])
    sent = {}
    monkeypatch.setattr(module.ThreadsAPI, "make_post", lambda *a, **k: sent.update(a=a, kw=k) or "t1")
    module.bot_post("j")
    assert sent["a"][2] == "oi" and "media_type" not in sent["kw"]
