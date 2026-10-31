"""Deterministic media compatibility planning for multi-network posts.

The caller owns persistence. Each network receives only what it accepts
(`adapt_media`): the rest is reported in `dropped`, never blocks the network.
A network is `blocked` only when nothing usable remains and plain text is not
allowed there.
"""

from dataclasses import dataclass, field
from typing import Literal

from api.network_limits import NETWORK_RULES, adapt_media, drop_reasons, media_kind, validate_post

MediaMode = Literal["none", "single_image", "carousel", "video", "text_only", "blocked"]


@dataclass(frozen=True)
class MediaPlan:
    network: str
    mode: MediaMode
    media_ids: list[int]
    text_variant: list[str]
    warnings: list[str]
    blocked_reason: str | None = None
    dropped: list[dict] = field(default_factory=list)


def _compatible_mode(medias: list[dict]) -> MediaMode:
    if not medias:
        return "none"
    kinds = [media_kind(media.get("file_name") or "") for media in medias]
    if len(medias) == 1 and kinds[0] == "video":
        return "video"
    if len(medias) == 1:
        return "single_image"
    return "carousel"


_TEXT_ERROR_KEYS = {"max_chars", "max_links", "max_hashtags", "max_mentions"}


def _undelivered_message(network: str, mode: MediaMode) -> str:
    label = NETWORK_RULES[network]["label"]
    names = {
        "single_image": "imagem única",
        "carousel": "carrossel",
        "video": "vídeo",
        "none": "post sem mídia",
    }
    return f"{label}: {names[mode]} ainda não é entregue por este aplicativo"


def plan_network_composition(
    network: str,
    texts: list[str],
    medias: list[dict],
    product_count: int = 0,
) -> MediaPlan:
    """Return the non-mutating plan for one selected network.

    Media the network cannot take is dropped (`dropped`), keeping the user's
    order for the rest. Text errors still block (the copy would be cut).
    """
    if network not in NETWORK_RULES:
        raise ValueError(f"Rede inválida: {network}")

    rule = NETWORK_RULES[network]
    label = rule["label"]
    # Não transmita respostas a redes sem formato de thread.
    publishable_texts = list(texts if rule["thread_parts"] else texts[:1])
    kept, dropped = adapt_media(network, medias)
    issues = validate_post(network, publishable_texts, kept, product_count)
    error_issues = [issue for issue in issues if issue["level"] == "error"]
    errors = [issue["message"] for issue in error_issues]
    warnings = [issue["message"] for issue in issues if issue["level"] == "warn"]
    if dropped and kept:
        warnings.insert(0, f"{label}: {len(kept)} de {len(medias)} mídias — {drop_reasons(dropped)}")

    def text_or_block(reason: str, notes: list[str]) -> MediaPlan:
        if rule["supports_text_only"]:
            return MediaPlan(network, "text_only", [], publishable_texts, notes + warnings, None, dropped)
        return MediaPlan(network, "blocked", [], publishable_texts, notes + warnings, reason, dropped)

    if any(issue.get("key") in _TEXT_ERROR_KEYS for issue in error_issues):
        return MediaPlan(network, "blocked", [], publishable_texts, errors + warnings, errors[0], dropped)
    if medias and not kept:
        reason = f"{label}: nenhuma mídia aceita ({drop_reasons(dropped)})"
        return text_or_block(reason, [reason])
    if errors:
        return text_or_block(errors[0], errors)

    mode = _compatible_mode(kept)
    if mode not in rule["delivered_modes"]:
        message = _undelivered_message(network, mode)
        return text_or_block(message, [message])

    return MediaPlan(
        network=network,
        mode=mode,
        media_ids=[media["id"] for media in kept],
        text_variant=publishable_texts,
        warnings=warnings,
        dropped=dropped,
    )
