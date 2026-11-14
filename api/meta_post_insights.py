"""Leitura de métricas por post no Instagram (mídia) e no Facebook (post de Página).

Mesmo contrato de post_insights.read_threads_post: (estado, métricas | None, extra).
Só consulta o ID do post publicado pelo Auto Orbital; nunca insights de conta/Página.
Métrica ausente na resposta = None (a UI mostra "—"), nunca 0.

Métricas conferidas na doc oficial em 14/11/2026 (página mostrava v27.0; o app usa v26.0):
- Instagram /{ig-media-id}/insights (FEED e REELS): views, reach, likes, comments,
  shares, saved. `impressions` foi depreciado para mídia criada após 02/07/2024 e
  `plays`/`video_views` não constam mais; não são pedidos. Filhos de carrossel não têm
  insights (o publicador guarda o ID do álbum). Atraso de até 48 h.
  Permissões (Facebook Login): instagram_basic, instagram_manage_insights, pages_read_engagement.
- Facebook /{post-id}/insights: post_media_view, post_total_media_view_unique,
  post_reactions_by_type_total. post_impressions* é obsoleto acima da v25 e não é pedido.
  Comentários e compartilhamentos vêm do próprio objeto Post (comments.summary, shares).
  Permissões: read_insights + pages_read_engagement, token de Página (tarefa ANALYZE),
  Página com 100+ curtidas. Atualização ~24 h.
"""
import re

import httpx

from apis.meta_version import GRAPH_BASE

IG_METRICS = ("views", "reach", "likes", "comments", "shares", "saved")
IG_FALLBACK = ("reach", "likes", "comments")
FB_METRICS = ("post_media_view", "post_total_media_view_unique", "post_reactions_by_type_total")
FB_FALLBACK = ("post_reactions_by_type_total",)
FB_POST_FIELDS = "shares,comments.limit(0).summary(true)"
_MEDIA_ID = re.compile(r"^[0-9]{1,40}$")
_FB_POST_ID = re.compile(r"^[0-9]{1,40}_[0-9]{1,40}$")
# Estados que dependem de o usuário reconectar a conta: não adianta seguir chamando a API.
RECONNECT_STATES = frozenset({"permission_required", "token_expired"})
STOP_STATES = RECONNECT_STATES | {"rate_limited"}
RATE_LIMIT_CODES = frozenset({4, 17, 32, 613})


def graph_error_state(response):
    """Classifica o erro da Graph API sem guardar mensagem bruta (pode citar o token)."""
    try:
        error = response.json().get("error") or {}
    except (ValueError, AttributeError):
        error = {}
    code = error.get("code") if isinstance(error, dict) else None
    subcode = error.get("error_subcode") if isinstance(error, dict) else None
    if code == 190 or response.status_code == 401:
        return "token_expired"
    if code in RATE_LIMIT_CODES or (isinstance(code, int) and 80000 <= code <= 80014) \
            or response.status_code == 429:
        return "rate_limited"
    if code == 10 or (isinstance(code, int) and 200 <= code <= 299) or response.status_code == 403:
        return "permission_required"
    if code == 100 and subcode == 33:
        return "not_found"  # Post removido na rede ou ID inexistente.
    if code == 100:
        return "invalid_metric"
    return "api_error"


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def insight_values(data):
    """{nome: valor} de uma resposta /insights; duplicata conflitante invalida tudo."""
    if not isinstance(data, list):
        return None
    values = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        if item["name"] in values:
            return None
        series = item.get("values")
        if isinstance(series, list) and len(series) == 1 and isinstance(series[0], dict):
            value = series[0].get("value")
        else:
            total = item.get("total_value")
            value = total.get("value") if isinstance(total, dict) else None
        values[item["name"]] = value
    return values


def parse_instagram_media_insights(data):
    values = insight_values(data)
    if not values:
        return None
    metrics = {"views": _count(values.get("views")), "reach": _count(values.get("reach")),
               "likes": _count(values.get("likes")), "comments": _count(values.get("comments")),
               "shares": _count(values.get("shares")), "saves": _count(values.get("saved"))}
    return metrics if any(value is not None for value in metrics.values()) else None


def _reactions(value):
    if not isinstance(value, dict):
        return None, None
    counts = {str(name)[:20]: _count(amount) for name, amount in value.items()}
    if any(amount is None for amount in counts.values()):
        return None, None
    return sum(counts.values()), counts


def parse_facebook_post(insights, post):
    """Junta /insights com os contadores do objeto Post; reações viram `likes`."""
    values = insight_values(insights) or {}
    likes, by_type = _reactions(values.get("post_reactions_by_type_total"))
    post = post if isinstance(post, dict) else {}
    shares = post.get("shares")
    summary = (post.get("comments") or {}).get("summary") if isinstance(post.get("comments"), dict) else None
    metrics = {
        "views": _count(values.get("post_media_view")),
        "reach": _count(values.get("post_total_media_view_unique")),
        "likes": likes,
        "comments": _count(summary.get("total_count")) if isinstance(summary, dict) else None,
        # Sem o campo `shares` a Graph API não diz se é zero: fica None.
        "shares": _count(shares.get("count")) if isinstance(shares, dict) else None,
        "saves": None,
    }
    extra = {"reactions_by_type": by_type} if by_type else {}
    return (metrics if any(value is not None for value in metrics.values()) else None), extra


async def _get(client, path, params, token):
    """GET na Graph API com token no header (nunca na URL, que pode ir para log)."""
    try:
        response = await client.get(f"{GRAPH_BASE}/{path}", params=params,
                                    headers={"Authorization": f"Bearer {token}"})
    except httpx.RequestError:
        return "network_error", None
    if response.status_code != 200:
        return graph_error_state(response), None
    try:
        body = response.json()
    except ValueError:
        return "invalid_response", None
    return ("ok", body) if isinstance(body, dict) else ("invalid_response", None)


async def _insights(client, object_id, token, attempts):
    """Tenta a lista completa e, se alguma métrica não existir para o tipo de mídia, a reduzida."""
    for metrics in attempts:
        state, body = await _get(client, f"{object_id}/insights", {"metric": ",".join(metrics)}, token)
        if state == "invalid_metric":
            continue
        if state != "ok":
            return state, None
        if not isinstance(body.get("data"), list):
            return "invalid_response", None
        return "ok", body["data"]
    return "api_error", None


async def read_instagram_media(client, external_id, token):
    if not isinstance(external_id, str) or not _MEDIA_ID.fullmatch(external_id):
        return "invalid_id", None, {}
    state, data = await _insights(client, external_id, token, (IG_METRICS, IG_FALLBACK))
    if state != "ok":
        return state, None, {}
    metrics = parse_instagram_media_insights(data)
    return ("ok" if metrics else "no_data"), metrics, {}


async def resolve_facebook_post_id(client, external_id, token):
    """O publicador guardava o ID da foto (/photos devolve `id` da foto e `post_id`).

    Foto -> `page_story_id` (doc do nó Photo). Vídeo (/videos) não tem o ID do post
    documentado no nó Video: fica `unsupported_type` em vez de inventar um ID.
    """
    if not isinstance(external_id, str):
        return "invalid_id", None
    if _FB_POST_ID.fullmatch(external_id):
        return "ok", external_id
    if not _MEDIA_ID.fullmatch(external_id):
        return "invalid_id", None
    state, body = await _get(client, external_id, {"fields": "page_story_id"}, token)
    if state == "invalid_metric":
        return "unsupported_type", None  # Campo inexistente: não é foto (vídeo).
    if state != "ok":
        return state, None
    story = body.get("page_story_id")
    return ("ok", story) if isinstance(story, str) and _FB_POST_ID.fullmatch(story) else ("sem_id", None)


async def read_facebook_post(client, external_id, token):
    state, post_id = await resolve_facebook_post_id(client, external_id, token)
    if state != "ok":
        return state, None, {}
    extra = {} if post_id == external_id else {"resolved_from": "photo"}
    state, data = await _insights(client, post_id, token, (FB_METRICS, FB_FALLBACK))
    if state != "ok":
        return state, None, extra
    post_state, post = await _get(client, post_id, {"fields": FB_POST_FIELDS}, token)
    if post_state in STOP_STATES or post_state == "not_found":
        return post_state, None, extra
    if post_state != "ok":
        extra["post_fields"] = post_state  # Comentários/compartilhamentos ficam None.
    metrics, detail = parse_facebook_post(data, post)
    return ("ok" if metrics else "no_data"), metrics, {**extra, **detail, "measured_id": post_id}
