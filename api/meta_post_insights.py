"""Leitura de métricas por post no Instagram (mídia) e no Facebook (post de Página).

Mesmo contrato de post_insights.read_threads_post: (estado, métricas | None, extra).
Só consulta o ID do post publicado pelo Auto Orbital; nunca insights de conta/Página.
Métrica ausente na resposta = None (a UI mostra "—"), nunca 0.

Métricas conferidas na doc oficial em 14/11/2026 (página mostrava v27.0; o app usa v26.0):
- Instagram /{ig-media-id}/insights (FEED e REELS): views, reach, likes, comments,
  shares, saved, reposts (FEED/REELS/STORY) e ig_reels_avg_watch_time (só REELS, ms;
  conferidos em 18/11/2026). FEED recusa ig_reels_avg_watch_time com code 100: cai na
  lista sem ele e, se ainda recusar, na reduzida. `impressions` foi depreciado para mídia criada após 02/07/2024 e
  `plays`/`video_views` não constam mais; não são pedidos. Filhos de carrossel não têm
  insights (o publicador guarda o ID do álbum). Atraso de até 48 h.
  Permissões (Facebook Login): instagram_basic, instagram_manage_insights, pages_read_engagement.
- Facebook /{post-id}/insights: post_media_view, post_total_media_view_unique,
  post_reactions_by_type_total. post_impressions* é obsoleto acima da v25 e não é pedido.
  Comentários e compartilhamentos vêm do próprio objeto Post (comments.summary, shares).
  Permissões: read_insights + pages_read_engagement, token de Página (tarefa ANALYZE),
  Página com 100+ curtidas. Atualização ~24 h.
- Facebook vídeo/Reels /{video-id}/video_insights (doc do nó Video Insights, conferida
  em 18/11/2026, exemplo em v27.0, period lifetime):
  Reels: blue_reels_play_count, post_impressions_unique, post_video_avg_time_watched (ms),
  post_video_likes_by_reaction_type, post_video_social_actions (comentários e
  compartilhamentos). Vídeo comum: total_video_views, total_video_impressions_unique,
  total_video_avg_time_watched (ms), total_video_reactions_by_type_total,
  total_video_stories_by_action_type. Reels primeiro; code 100 cai na lista de vídeo
  comum e depois na reduzida. Permissões da doc: read_insights + pages_manage_engagement
  (tarefa ANALYZE). Sem pages_manage_engagement a Meta responde 10/200: vira
  `access_denied` (não pede reconexão nem para a coleta dos outros posts).
"""
import logging
import re

import httpx

from apis.meta_version import GRAPH_BASE

IG_BASE_METRICS = ("views", "reach", "likes", "comments", "shares", "saved")
IG_FEED_METRICS = IG_BASE_METRICS + ("reposts",)
IG_METRICS = IG_FEED_METRICS + ("ig_reels_avg_watch_time",)
IG_FALLBACK = ("reach", "likes", "comments")
IG_ATTEMPTS = (IG_METRICS, IG_FEED_METRICS, IG_BASE_METRICS, IG_FALLBACK)
FB_METRICS = ("post_media_view", "post_total_media_view_unique", "post_reactions_by_type_total")
FB_FALLBACK = ("post_reactions_by_type_total",)
FB_POST_FIELDS = "shares,comments.limit(0).summary(true)"
FB_REELS_METRICS = ("blue_reels_play_count", "post_impressions_unique", "post_video_avg_time_watched",
                    "post_video_likes_by_reaction_type", "post_video_social_actions")
FB_VIDEO_METRICS = ("total_video_views", "total_video_impressions_unique", "total_video_avg_time_watched",
                    "total_video_reactions_by_type_total", "total_video_stories_by_action_type")
FB_VIDEO_FALLBACK = ("total_video_views",)
FB_VIDEO_ATTEMPTS = (FB_REELS_METRICS, FB_VIDEO_METRICS, FB_VIDEO_FALLBACK)
VIDEO_PERMISSION_REASON = "video_insights_permission"
_MEDIA_ID = re.compile(r"^[0-9]{1,40}$")
_FB_POST_ID = re.compile(r"^[0-9]{1,40}_[0-9]{1,40}$")
# Estados que dependem de o usuário reconectar a conta: não adianta seguir chamando a API.
RECONNECT_STATES = frozenset({"permission_required", "token_expired"})
STOP_STATES = RECONNECT_STATES | {"rate_limited"}
# A Meta só entrega insights de Páginas com 100 curtidas ou mais; abaixo disso /insights
# responde 200 sem métricas. Estado informativo: não pede reconexão nem interrompe a coleta.
MIN_PAGE_FANS = 100
AUDIENCE_BELOW_MINIMUM = "audience_below_minimum"
PAGE_AUDIENCE_FIELDS = "fan_count,followers_count"
RATE_LIMIT_CODES = frozenset({4, 17, 32, 613})
# Só a presença destes termos na mensagem decide; a mensagem em si nunca é guardada nem logada.
_PERMISSION_MESSAGE = re.compile(r"permiss|read_insights|pages_read_engagement", re.IGNORECASE)
_ERROR_TYPE = re.compile(r"^[A-Za-z]{1,40}$")
_PATH_IDS = re.compile(r"[0-9]+(?:_[0-9]+)?")

logger = logging.getLogger(__name__)


def _graph_error(response):
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        error = None
    return error if isinstance(error, dict) else {}


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def graph_error_info(response):
    """Só números/enum do erro (code, subcode, type): seguro para log e para `extra`."""
    error = _graph_error(response)
    kind = error.get("type")
    return {"graph_code": _int(error.get("code")), "graph_subcode": _int(error.get("error_subcode")),
            "graph_type": kind if isinstance(kind, str) and _ERROR_TYPE.fullmatch(kind) else None}


def graph_error_state(response):
    """Classifica o erro da Graph API sem guardar mensagem bruta (pode citar o token).

    `permission_required` (reconecte) só quando a Meta aponta permissão: code 200-299 ou
    code 10 com mensagem de permissão. 403 sem code reconhecido e code 10 sem essa
    mensagem viram `access_denied` (ex.: Página com menos de 100 curtidas), que não pede
    reconexão.
    """
    error = _graph_error(response)
    code = _int(error.get("code"))
    subcode = _int(error.get("error_subcode"))
    if code == 190 or response.status_code == 401:
        return "token_expired"
    if code in RATE_LIMIT_CODES or (code is not None and 80000 <= code <= 80014)             or response.status_code == 429:
        return "rate_limited"
    if code is not None and 200 <= code <= 299:
        return "permission_required"
    if code == 10:
        message = error.get("message")
        if isinstance(message, str) and _PERMISSION_MESSAGE.search(message):
            return "permission_required"
        return "access_denied"
    if code == 100 and subcode == 33:
        return "not_found"  # Post removido na rede ou ID inexistente.
    if code == 100:
        return "invalid_metric"
    if response.status_code == 403:
        return "access_denied"
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
               "shares": _count(values.get("shares")), "saves": _count(values.get("saved")),
               "reposts": _count(values.get("reposts"))}
    return metrics if any(value is not None for value in metrics.values()) else None


def watch_time_extra(values, name):
    """Tempo médio assistido (ms) vai para `extra`: não há coluna própria."""
    value = _count((values or {}).get(name))
    return {"avg_watch_time_ms": value} if value is not None else {}


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
    """GET na Graph API com token no header (nunca na URL, que pode ir para log).

    Em erro, o segundo valor traz só graph_code/graph_subcode (números) para o `extra`.
    """
    try:
        response = await client.get(f"{GRAPH_BASE}/{path}", params=params,
                                    headers={"Authorization": f"Bearer {token}"})
    except httpx.RequestError:
        return "network_error", None
    if response.status_code != 200:
        info = graph_error_info(response)
        logger.warning("Graph API GET %s falhou: status=%s code=%s subcode=%s type=%s",
                       _PATH_IDS.sub("{id}", path), response.status_code, info["graph_code"],
                       info["graph_subcode"], info["graph_type"])
        return graph_error_state(response), {"graph_code": info["graph_code"],
                                             "graph_subcode": info["graph_subcode"]}
    try:
        body = response.json()
    except ValueError:
        return "invalid_response", None
    return ("ok", body) if isinstance(body, dict) else ("invalid_response", None)


async def _insights(client, object_id, token, attempts, edge="insights"):
    """Tenta a lista completa e, se alguma métrica não existir para o tipo de mídia, a reduzida."""
    for metrics in attempts:
        state, body = await _get(client, f"{object_id}/{edge}", {"metric": ",".join(metrics)}, token)
        if state == "invalid_metric":
            continue
        if state != "ok":
            return state, body  # body = código do erro (ou None)
        if not isinstance(body.get("data"), list):
            return "invalid_response", None
        return "ok", body["data"]
    return "api_error", None


async def read_instagram_media(client, external_id, token):
    if not isinstance(external_id, str) or not _MEDIA_ID.fullmatch(external_id):
        return "invalid_id", None, {}
    state, data = await _insights(client, external_id, token, IG_ATTEMPTS)
    if state != "ok":
        return state, None, {}
    metrics = parse_instagram_media_insights(data)
    extra = watch_time_extra(insight_values(data), "ig_reels_avg_watch_time") if metrics else {}
    return ("ok" if metrics else "no_data"), metrics, extra


async def resolve_facebook_post_id(client, external_id, token):
    """O publicador guardava o ID da foto (/photos devolve `id` da foto e `post_id`).

    Foto -> `page_story_id` (doc do nó Photo). Vídeo (/videos) não tem o ID do post
    documentado no nó Video: devolve `unsupported_type` e read_facebook_post mede o
    próprio vídeo em /video_insights (sem inventar um ID de post).
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
        return state, body  # body = código do erro (ou None)
    story = body.get("page_story_id")
    return ("ok", story) if isinstance(story, str) and _FB_POST_ID.fullmatch(story) else ("sem_id", None)


def _action_counts(value):
    """{"comment": n, "share": n, ...} de social_actions/stories_by_action_type (chaves sem caixa)."""
    if not isinstance(value, dict):
        return None, None
    counts = {str(key).lower(): _count(amount) for key, amount in value.items()}
    return counts.get("comment"), counts.get("share")


def parse_facebook_video(data):
    """Reels ou vídeo comum (o que vier); reações viram `likes`, tempo médio vai para `extra`."""
    values = insight_values(data) or {}
    reels = any(name in values for name in FB_REELS_METRICS)
    names = FB_REELS_METRICS if reels else FB_VIDEO_METRICS
    likes, by_type = _reactions(values.get(names[3]))
    comments, shares = _action_counts(values.get(names[4]))
    metrics = {"views": _count(values.get(names[0])), "reach": _count(values.get(names[1])),
               "likes": likes, "comments": comments, "shares": shares, "saves": None}
    extra = {"measured_as": "reels" if reels else "video", **watch_time_extra(values, names[2])}
    if by_type:
        extra["reactions_by_type"] = by_type
    return (metrics if any(value is not None for value in metrics.values()) else None), extra


async def read_facebook_video(client, video_id, token):
    """Vídeo/Reels publicado pelo app (ID do vídeo). Falta de permissão = access_denied."""
    state, data = await _insights(client, video_id, token, FB_VIDEO_ATTEMPTS, edge="video_insights")
    if state == "permission_required":
        return "access_denied", None, {"reason": VIDEO_PERMISSION_REASON, **_failure("video_insights", data)}
    if state != "ok":
        return state, None, _failure("video_insights", data)
    metrics, extra = parse_facebook_video(data)
    return ("ok" if metrics else "no_data"), metrics, {**extra, "measured_id": video_id}


def _failure(step, info):
    """Qual chamada falhou e com qual código; nunca mensagem, token ou ID."""
    return {"step": step, **(info or {})}


async def read_facebook_post(client, external_id, token):
    state, post_id = await resolve_facebook_post_id(client, external_id, token)
    if state == "unsupported_type":
        return await read_facebook_video(client, external_id, token)  # vídeo/Reels: ID do vídeo
    if state != "ok":
        return state, None, _failure("resolve", post_id if isinstance(post_id, dict) else None)
    extra = {} if post_id == external_id else {"resolved_from": "photo"}
    state, data = await _insights(client, post_id, token, (FB_METRICS, FB_FALLBACK))
    if state != "ok":
        return state, None, {**extra, **_failure("insights", data)}
    post_state, post = await _get(client, post_id, {"fields": FB_POST_FIELDS}, token)
    if post_state in ("token_expired", "rate_limited", "not_found"):
        return post_state, None, {**extra, **_failure("post_fields", post)}
    if post_state != "ok":
        # Insights já obtidos ficam; comentários/compartilhamentos viram None (traço).
        extra["post_fields"] = {"state": post_state, **_failure("post_fields", post)}
        post = None
    metrics, detail = parse_facebook_post(data, post)
    return ("ok" if metrics else "no_data"), metrics, {**extra, **detail, "measured_id": post_id}


async def read_page_audience(client, page_id, token):
    """Curtidas e seguidores da Página (token de Página). Qualquer falha devolve None."""
    page_id = str(page_id or "")
    if not _MEDIA_ID.fullmatch(page_id):
        return None
    try:
        state, body = await _get(client, page_id, {"fields": PAGE_AUDIENCE_FIELDS}, token)
    except Exception as err:  # Nunca derruba a coleta dos posts.
        logger.warning("Leitura de curtidas da Página falhou: %s", type(err).__name__)
        return None
    fans = _count(body.get("fan_count")) if state == "ok" else None
    if fans is None:
        return None
    return {"fan_count": fans, "followers_count": _count(body.get("followers_count"))}


def classify_page_audience(state, audience):
    """`no_data` numa Página com menos de 100 curtidas vira `audience_below_minimum`."""
    if state == "no_data" and audience and audience["fan_count"] < MIN_PAGE_FANS:
        return AUDIENCE_BELOW_MINIMUM
    return state
