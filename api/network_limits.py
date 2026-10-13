"""
Regras de publicação por rede — espelho de frontend/src/lib/networkLimits.ts
(fontes oficiais e data de consulta estão lá; mudou um número lá, mude aqui).

O servidor recusa o que o front já bloqueia, pra ninguém burlar a UI. Só
valida o que dá pra saber sem decodificar o arquivo: texto, links, hashtags,
@menções, quantidade/tipo/formato/tamanho das mídias e mistura. Duração,
resolução e proporção de vídeo/imagem ficam só no navegador (exigiria
ffprobe/Pillow no servidor).

Limites em `unverified` não constam da doc oficial: viram aviso, não erro.
"""

import re

MB = 1024 * 1024
GB = 1024 * MB

NETWORK_RULES = {
    "threads": {
        "label": "Threads", "max_chars": 500, "count": "codepoints", "thread_parts": True,
        "supports_text_only": True,
        "delivered_modes": {"none", "single_image", "carousel", "video", "text_only"},
        "max_links": 5, "max_hashtags": 1, "max_media": 20, "allow_mix": True,
        "exts": {"jpg", "jpeg", "png", "mp4"},
        "max_bytes": {"image": 8 * MB, "video": 1 * GB},
        "unverified": set(),
    },
    "x": {
        "label": "X", "max_chars": 280, "count": "weighted", "thread_parts": True,
        "supports_text_only": True,
        "delivered_modes": {"none", "single_image", "text_only"},
        "max_image": 4, "max_gif": 1, "max_video": 1, "allow_mix": False,
        "exts": {"jpg", "jpeg", "png", "webp", "gif", "mp4"},
        "max_bytes": {"image": 5 * MB, "gif": 15 * MB, "video": 8 * GB},
        "unverified": {"exts"},
    },
    "facebook": {
        "label": "Facebook", "max_chars": 63206, "count": "codepoints", "thread_parts": False,
        "supports_text_only": True,
        "delivered_modes": {"none", "single_image", "carousel", "video", "text_only"},
        "max_gif": 1, "max_video": 1, "allow_mix": False,
        "exts": {"jpg", "jpeg", "png", "gif", "mp4"},
        "max_bytes": {"image": 4 * MB, "gif": 4 * MB},
        "unverified": {"max_chars"},
    },
    "instagram": {
        "label": "Instagram", "max_chars": 2200, "count": "codepoints", "thread_parts": False,
        "supports_text_only": False,
        "delivered_modes": {"single_image", "carousel", "video"},
        "max_hashtags": 30, "max_mentions": 20, "max_media": 10, "allow_mix": True,
        "requires_media": "media-or-product",
        "exts": {"jpg", "jpeg", "mp4"},
        "max_bytes": {"image": 8 * MB, "video": 300 * MB},
        "unverified": set(),
    },
    "tiktok": {
        "label": "TikTok", "max_chars": 2200, "count": "utf16", "thread_parts": False,
        "supports_text_only": False,
        # Foto (Photo Direct Post) segue bloqueada: sem Creator Info/UI de privacidade
        # nem domínio/prefixo de URL verificado no TikTok (ver apis/tiktok.py).
        "delivered_modes": {"video"},
        "max_image": 0, "max_gif": 0, "max_video": 1, "allow_mix": False,
        "requires_media": "video",
        "exts": {"mp4"},
        "max_bytes": {"video": 4 * GB},
        "unverified": set(),
    },
}

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"#\w+")
_MENTION_RE = re.compile(r"@[\w.]+")
# Pesos do twitter-text (config v3): estas faixas pesam 1, o resto 2.
_X_LIGHT = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
_KIND_LABEL = {"image": "imagem", "gif": "GIF", "video": "vídeo"}


def text_length(rule: dict, text: str) -> int:
    if rule["count"] == "utf16":
        return len(text.encode("utf-16-le")) // 2
    if rule["count"] == "codepoints":
        return len(text)
    total = len(_URL_RE.findall(text)) * 23
    for ch in _URL_RE.sub("", text):
        cp = ord(ch)
        total += 1 if any(a <= cp <= b for a, b in _X_LIGHT) else 2
    return total


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def media_kind(name: str) -> str:
    ext = _ext(name)
    return "video" if ext == "mp4" else "gif" if ext == "gif" else "image"


def _fmt_bytes(b: int) -> str:
    return f"{b // GB} GB" if b >= GB else f"{round(b / MB)} MB"


def validate_post(
    network: str,
    texts: list[str],
    medias: list[dict],
    product_count: int = 0,
    check_required_media: bool = True,
) -> list[dict]:
    """Lista de problemas `{"level": "error"|"warn", "message": str}`.

    `medias`: dicts com `file_name` e `size` (linhas de `medias`).
    `check_required_media=False` na criação/upload: a mídia de um post novo
    só sobe DEPOIS de criado, então "exige vídeo" é cobrado no /publish."""
    rule = NETWORK_RULES[network]
    issues: list[dict] = []

    def add(key: str, message: str) -> None:
        soft = key in rule["unverified"]
        suffix = " (limite não confirmado)" if soft else ""
        issues.append({
            "key": key,
            "level": "warn" if soft else "error",
            "message": f"{rule['label']}: {message}{suffix}",
        })

    parts = texts if rule["thread_parts"] else texts[:1]
    for i, text in enumerate(parts):
        where = f" na parte {i + 1}" if len(parts) > 1 else ""
        length = text_length(rule, text)
        if length > rule["max_chars"]:
            add("max_chars", f"texto máx. {rule['max_chars']} caracteres{where} (você tem {length})")
        for key, regex, label in (
            ("max_links", _URL_RE, "links"),
            ("max_hashtags", _HASHTAG_RE, "hashtag(s)"),
            ("max_mentions", _MENTION_RE, "@menções"),
        ):
            n = len(regex.findall(text))
            if key in rule and n > rule[key]:
                add(key, f"máx. {rule[key]} {label}{where} (você tem {n})")
    if not rule["thread_parts"] and len(texts) > 1:
        issues.append({
            "key": "thread_parts",
            "level": "warn",
            "message": f"{rule['label']}: só a 1ª parte é publicada (sem thread)",
        })

    kinds = [media_kind(m.get("file_name") or "") for m in medias]
    if check_required_media:
        if rule.get("requires_media") == "video" and "video" not in kinds:
            add("requires_media", "exige 1 vídeo (.mp4)")
        if rule.get("requires_media") == "media-or-product" and not medias and not product_count:
            add("requires_media", "exige imagem/vídeo (ou um produto com foto)")
    if "max_media" in rule and len(medias) > rule["max_media"]:
        add("max_media", f"máx. {rule['max_media']} mídias (você tem {len(medias)})")
    for kind in ("image", "gif", "video"):
        key, n = f"max_{kind}", kinds.count(kind)
        if key in rule and n > rule[key]:
            add(key, f"não aceita {_KIND_LABEL[kind]}" if rule[key] == 0
                else f"máx. {rule[key]} {_KIND_LABEL[kind]}(s) (você tem {n})")
    if rule.get("allow_mix") is False and len(set(kinds)) > 1:
        add("allow_mix", "não mistura imagem, GIF e vídeo no mesmo post")

    for media, kind in zip(medias, kinds):
        name = media.get("file_name") or ""
        if _ext(name) not in rule["exts"]:
            allowed = ", ".join(f".{e}" for e in sorted(rule["exts"]))
            add("exts", f"não aceita .{_ext(name)} ({name}); use {allowed}")
            continue
        max_b = rule["max_bytes"].get(kind)
        if max_b is not None and (media.get("size") or 0) > max_b:
            add("max_bytes", f"{name} passa de {_fmt_bytes(max_b)}")
    return issues


def errors_detail(issues: list[dict]) -> str | None:
    """Mensagem única pro HTTPException, ou None se só há avisos."""
    errors = [i["message"] for i in issues if i["level"] == "error"]
    return "; ".join(errors) if errors else None

