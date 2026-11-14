"""Espera do contêiner do Threads antes de threads_publish (sem dormir de verdade)."""

import pytest

from shopee_bot.apis import threads


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        assert seconds >= 0
        self.now += seconds


@pytest.fixture
def graph(monkeypatch):
    """Graph API simulada: statuses é a fila de respostas do GET de status."""
    clock = FakeClock()
    state = {"statuses": [], "calls": [], "clock": clock}
    monkeypatch.setattr(threads, "_sleep", clock.sleep)
    monkeypatch.setattr(threads, "_monotonic", clock.monotonic)

    def create(*args, **kwargs):
        state["calls"].append(("create", clock.now))
        return f"c{len(state['calls'])}"

    def status(token, container_id):
        state["calls"].append(("status", clock.now))
        nxt = state["statuses"].pop(0) if state["statuses"] else {"status": "IN_PROGRESS"}
        return nxt

    def publish(user_id, token, container_id):
        state["calls"].append(("publish", clock.now))
        return "published-1"

    monkeypatch.setattr(threads, "_create_media_container", create)
    monkeypatch.setattr(threads, "_create_carousel_item", create)
    monkeypatch.setattr(threads, "_create_carousel_container", create)
    monkeypatch.setattr(threads, "_get_media_container_status", status)
    monkeypatch.setattr(threads, "_publish_media_container", publish)
    return state


def _time_of(state, kind):
    return [t for k, t in state["calls"] if k == kind]


def test_publica_so_30s_apos_criar_mesmo_com_finished_imediato(graph):
    graph["statuses"] = [{"status": "FINISHED"}]

    assert threads.make_post("u", "tok", "oi") == "published-1"

    created = _time_of(graph, "create")[0]
    published = _time_of(graph, "publish")[0]
    assert published - created >= threads.MIN_WAIT_BEFORE_PUBLISH_S


def test_exige_finished_e_consulta_com_intervalo(graph):
    graph["statuses"] = [{"status": "IN_PROGRESS"}, {"status": "IN_PROGRESS"}, {"status": "FINISHED"}]

    threads.make_post("u", "tok", "oi")

    polls = _time_of(graph, "status")
    assert len(polls) == 3
    assert polls[1] - polls[0] == threads.POLL_INTERVAL_S
    assert _time_of(graph, "publish")[0] >= polls[-1]


def test_timeout_de_5_min_falha_claro_sem_publicar(graph):
    with pytest.raises(threads.ThreadsContainerError, match="não ficou pronto em 5 min"):
        threads.make_post("u", "tok", "oi")

    assert _time_of(graph, "publish") == []
    created = _time_of(graph, "create")[0]
    assert _time_of(graph, "status")[-1] - created <= threads.MAX_WAIT_S


@pytest.mark.parametrize("status", ["ERROR", "EXPIRED"])
def test_error_ou_expired_falha_claro_sem_publicar(graph, status):
    graph["statuses"] = [{"status": status, "error_message": "FAILED_PROCESSING_IMAGE"}]

    with pytest.raises(threads.ThreadsContainerError, match=status):
        threads.make_post("u", "tok", "oi")

    assert _time_of(graph, "publish") == []


def test_carrossel_espera_itens_e_contêiner_antes_de_publicar(graph):
    graph["statuses"] = [{"status": "FINISHED"}] * 3
    medias = [{"type": "IMAGE", "url": "https://x/a.jpg"}, {"type": "IMAGE", "url": "https://x/b.jpg"}]

    threads.make_carousel_post("u", "tok", "oi", medias)

    creates = _time_of(graph, "create")
    # Os dois itens são criados juntos (os 30 s correm em paralelo).
    assert creates[1] == creates[0]
    carousel_created = creates[2]
    assert carousel_created - creates[0] >= threads.MIN_WAIT_BEFORE_PUBLISH_S
    assert _time_of(graph, "publish")[0] - carousel_created >= threads.MIN_WAIT_BEFORE_PUBLISH_S
