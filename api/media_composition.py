"""Deterministic media compatibility planning for multi-network posts.

The caller owns persistence. This module only decides what a single network
can receive, so a rejected composition never cancels compatible networks.
"""

from dataclasses import dataclass
from typing import Literal

from api.network_limits import NETWORK_RULES, media_kind, validate_post

MediaMode = Literal["none", "single_image", "carousel", "video", "text_only", "blocked"]


@dataclass(frozen=True)
class MediaPlan:
    network: str
    mode: MediaMode
    media_ids: list[int]
    text_variant: list[str]
    warnings: list[str]
    blocked_reason: str | None = None


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

    Validation errors become a text-only fallback only when the provider API
    supports a post without media. Otherwise that network is blocked while the
    caller remains free to create the other networks' posts.
    """
    if network not in NETWORK_RULES:
        raise ValueError(f"Rede inválida: {network}")

    issues = validate_post(network, texts, medias, product_count)
    error_issues = [issue for issue in issues if issue["level"] == "error"]
    errors = [issue["message"] for issue in error_issues]
    warnings = [issue["message"] for issue in issues if issue["level"] == "warn"]

    if errors:
        has_text_error = any(issue.get("key") in _TEXT_ERROR_KEYS for issue in error_issues)
        if not has_text_error and NETWORK_RULES[network]["supports_text_only"]:
            return MediaPlan(network, "text_only", [], list(texts), errors + warnings)
        return MediaPlan(network, "blocked", [], list(texts), errors + warnings, errors[0])

    mode = _compatible_mode(medias)
    if mode not in NETWORK_RULES[network]["delivered_modes"]:
        message = _undelivered_message(network, mode)
        if NETWORK_RULES[network]["supports_text_only"]:
            return MediaPlan(network, "text_only", [], list(texts), warnings + [message])
        return MediaPlan(network, "blocked", [], list(texts), warnings + [message], message)

    return MediaPlan(
        network=network,
        mode=mode,
        media_ids=[media["id"] for media in medias],
        text_variant=list(texts),
        warnings=warnings,
    )
