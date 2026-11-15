"""Falha ANTES do passo que publica = failed; falha no passo que publica = unknown.

Criar e aguardar contêiner não torna nada público. Só a chamada final
(threads_publish / media_publish / init do TikTok) pode ter publicado
mesmo quando a resposta se perde: só ela fica 'unknown'.
"""

import sys

import pytest

import shopee_bot.scheduler.bot_post  # noqa: F401
import shopee_bot.scheduler.bot_post_instagram  # noqa: F401
import shopee_bot.scheduler.bot_post_facebook  # noqa: F401
from shopee_bot.apis import threads, instagram
from shopee_bot.scheduler import media_delivery
from shopee_bot.utils import was_not_published
from tests.scheduler.meta_fakes import FakeStorage

bot_threads = sys.modules["shopee_bot.scheduler.bot_post"]
bot_instagram = sys.modules["shopee_bot.scheduler.bot_post_instagram"]
bot_facebook = sys.modules["shopee_bot.scheduler.bot_post_facebook"]


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def threads_graph(monkeypatch):
    clock = FakeClock()
    state = {"statuses": [], "published": 0, "publish_error": None}
    monkeypatch.setattr(threads, "_sleep", clock.sleep)
    monkeypatch.setattr(threads, "_monotonic", clock.monotonic)
    monkeypatch.setattr(threads, "_create_media_container", lambda *a, **k: "c1")
    monkeypatch.setattr(threads, "_create_carousel_item", lambda *a, **k: "i1")
    monkeypatch.setattr(threads, "_create_carousel_container", lambda *a, **k: "car1")
    monkeypatch.setattr(threads, "_get_media_container_status",
                        lambda token, cid: state["statuses"].pop(0) if state["statuses"] else {"status": "IN_PROGRESS"})

    def publish(*_args):
        state["published"] += 1
        if state["publish_error"]:
            raise state["publish_error"]
        return "t-1"

    monkeypatch.setattr(threads, "_publish_media_container", publish)

    storage = FakeStorage()
    monkeypatch.setattr(media_delivery, "_storage", lambda: storage)
    monkeypatch.setattr(bot_threads.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(bot_threads.threads_credentials, "get_by_user_id",
                        lambda u, p: {"username": "u", "threads_user_id": "tu", "threads_access_token": "tok"})
    state["parts"] = [{"text": "oi", "medias": []}]
    monkeypatch.setattr(bot_threads.posts, "get", lambda u, post, p: state["parts"])
    state["activities"] = []
    monkeypatch.setattr(bot_threads, "insert_activities",
                        lambda u, t, m, profile_id=None: state["activities"].append(m))
    return state


def test_threads_timeout_na_espera_do_conteiner_e_failed(threads_graph):
    result = bot_threads.bot_post("j")
    assert result.status == "failed"
    assert "não ficou pronto" in result.error
    assert threads_graph["published"] == 0


@pytest.mark.parametrize("status", ["ERROR", "EXPIRED"])
def test_threads_conteiner_error_ou_expired_e_failed(threads_graph, status):
    threads_graph["statuses"] = [{"status": status, "error_message": "FAILED_PROCESSING"}]
    result = bot_threads.bot_post("j")
    assert result.status == "failed"
    assert status in result.error
    assert threads_graph["published"] == 0


def test_threads_falha_ao_consultar_status_e_failed(threads_graph, monkeypatch):
    def broken(*_args):
        raise threads.ThreadsApiError("Failed to Get Media Container Status", 500)
    monkeypatch.setattr(threads, "_get_media_container_status", broken)
    assert bot_threads.bot_post("j").status == "failed"


def test_threads_criacao_5xx_tambem_e_failed(threads_graph, monkeypatch):
    def broken(*_args, **_kwargs):
        raise threads.ThreadsApiError("Failed to Create Media Container", 502)
    monkeypatch.setattr(threads, "_create_media_container", broken)
    assert bot_threads.bot_post("j").status == "failed"


def test_threads_erro_no_threads_publish_continua_unknown(threads_graph):
    threads_graph["statuses"] = [{"status": "FINISHED"}]
    threads_graph["publish_error"] = threads.ThreadsApiError("Failed to Publish Media Container", 500)
    result = bot_threads.bot_post("j")
    assert result.status == "unknown"
    assert threads_graph["published"] == 1


def test_threads_resposta_perdida_no_publish_continua_unknown(threads_graph):
    threads_graph["statuses"] = [{"status": "FINISHED"}]
    threads_graph["publish_error"] = ConnectionError("conexão caiu depois do POST")
    assert bot_threads.bot_post("j").status == "unknown"


def test_threads_espera_falha_na_segunda_parte_fica_unknown(threads_graph):
    # Parte 1 publicada; parte 2 nem chegou ao publish. Reenviar duplicaria
    # a parte 1, então o job inteiro segue sem confirmação (falha parcial).
    threads_graph["parts"] = [{"text": "1", "medias": []}, {"text": "2", "medias": []}]
    threads_graph["statuses"] = [{"status": "FINISHED"}, {"status": "ERROR"}]
    result = bot_threads.bot_post("j")
    assert result.status == "unknown"
    assert threads_graph["activities"][0]["metadata"]["published_parts"] == 1


def test_threads_carrossel_espera_falha_e_failed(threads_graph):
    threads_graph["parts"] = [{"text": "oi", "medias": [
        {"type": "IMAGE", "file_path": "storage://b/a.jpg", "file_name": "a.jpg"},
        {"type": "IMAGE", "file_path": "storage://b/b.jpg", "file_name": "b.jpg"},
    ]}]
    threads_graph["statuses"] = [{"status": "FINISHED"}, {"status": "EXPIRED"}]
    assert bot_threads.bot_post("j").status == "failed"
    assert threads_graph["published"] == 0


def test_marca_fica_so_nas_falhas_antes_do_publish(threads_graph):
    threads_graph["statuses"] = [{"status": "ERROR"}]
    with pytest.raises(threads.ThreadsContainerError) as caught:
        threads.make_post("u", "tok", "oi")
    assert was_not_published(caught.value)

    threads_graph["statuses"] = [{"status": "FINISHED"}]
    threads_graph["publish_error"] = threads.ThreadsApiError("Failed to Publish Media Container", 500)
    with pytest.raises(threads.ThreadsApiError) as caught:
        threads.make_post("u", "tok", "oi")
    assert not was_not_published(caught.value)


# --- Instagram: mesmo padrão (contêiner + espera + media_publish) -------------

@pytest.fixture
def instagram_graph(monkeypatch):
    state = {"published": 0, "poll_error": None, "publish_error": None}
    monkeypatch.setattr(instagram, "_app_access_token", lambda *a: "app")
    monkeypatch.setattr(instagram, "_resolve_ig_user_id", lambda token, ig=None: "ig1")
    monkeypatch.setattr(instagram, "_create_image_media_container", lambda *a: "c1")

    def poll(*_args, **_kwargs):
        if state["poll_error"]:
            raise state["poll_error"]
        return True

    def publish(*_args):
        state["published"] += 1
        if state["publish_error"]:
            raise state["publish_error"]
        return "m1"

    monkeypatch.setattr(instagram, "_poll_media_container", poll)
    monkeypatch.setattr(instagram, "_publish_media_container", publish)

    storage = FakeStorage()
    monkeypatch.setattr(media_delivery, "_storage", lambda: storage)
    monkeypatch.setattr(bot_instagram.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(bot_instagram.instagram_credentials, "get_by_user_id", lambda u, p=None: {
        "username": "u", "instagram_app_id": "a", "instagram_secret": "s",
        "instagram_user_access_token": "tok", "instagram_ig_user_id": "ig1",
    })
    monkeypatch.setattr(bot_instagram.posts, "get", lambda u, post, p: [{"text": "oi", "medias": [
        {"type": "IMAGE", "file_path": "storage://b/a.jpg", "file_name": "a.jpg"}]}])
    monkeypatch.setattr(bot_instagram, "insert_activities", lambda *a, **k: None)
    return state


def test_instagram_conteiner_em_erro_e_failed(instagram_graph):
    instagram_graph["poll_error"] = Exception("Instagram: container em estado ERROR")
    assert bot_instagram.bot_post_instagram("j").status == "failed"
    assert instagram_graph["published"] == 0


def test_instagram_erro_no_media_publish_continua_unknown(instagram_graph):
    instagram_graph["publish_error"] = Exception("Instagram: falha ao publicar (status 500)")
    assert bot_instagram.bot_post_instagram("j").status == "unknown"


# --- Facebook: validação local antes de qualquer chamada ----------------------

def test_facebook_validacao_local_sem_token_de_pagina_e_failed(monkeypatch):
    monkeypatch.setattr(bot_facebook.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(bot_facebook.facebook_credentials, "get_by_user_id", lambda u, p=None: {
        "username": "u", "facebook_app_id": "a", "facebook_secret": "s",
        "facebook_page_id": "pg", "facebook_page_access_token": None,
    })
    monkeypatch.setattr(bot_facebook.posts, "get", lambda u, post, p: [{"text": "oi", "product_ids": [], "medias": [
        {"type": "IMAGE", "file_path": "storage://b/a.jpg", "file_name": "a.jpg"}]}])
    monkeypatch.setattr(bot_facebook, "insert_activities", lambda *a, **k: None)
    monkeypatch.setattr(bot_facebook, "mark_external_delivery",
                        lambda: (_ for _ in ()).throw(AssertionError("não deveria enviar")))
    result = bot_facebook.bot_post_facebook("j")
    assert result.status == "failed"
    assert "token de Página" in result.error


def test_facebook_erro_da_api_continua_unknown(monkeypatch):
    monkeypatch.setattr(bot_facebook.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(bot_facebook.facebook_credentials, "get_by_user_id", lambda u, p=None: {
        "username": "u", "facebook_app_id": "a", "facebook_secret": "s",
        "facebook_page_id": "pg", "facebook_page_access_token": "ptok",
    })
    monkeypatch.setattr(bot_facebook.posts, "get", lambda u, post, p: [{"text": "oi", "product_ids": [], "medias": []}])
    monkeypatch.setattr(bot_facebook, "insert_activities", lambda *a, **k: None)
    monkeypatch.setattr(bot_facebook, "mark_external_delivery", lambda: None)
    monkeypatch.setattr(bot_facebook.FacebookAPI, "post_text_as_page",
                        lambda *a: (_ for _ in ()).throw(TimeoutError("sem resposta")))
    assert bot_facebook.bot_post_facebook("j").status == "unknown"
