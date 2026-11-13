"""Troca, só no texto enviado, o link Shopee pelo redirecionador próprio /r/{token}.

Um token opaco por (envio, destino); retentativa do mesmo envio reaproveita o token.
Qualquer falha (sem CLICK_REDIRECT_BASE_URL, tabela ausente, banco, limite de texto)
mantém o link direto: a publicação nunca é bloqueada por isto. Nada é persistido
no post; o texto original do usuário continua intacto.
"""
import os
import re
import secrets
from urllib.parse import urlsplit

from shopee_bot.clogging import logger
from shopee_bot.database import query_db
from api.network_limits import NETWORK_RULES, text_length
from api.shopee_affiliate_links import is_safe_shopee_link

_LINK = re.compile(r"https://[^\s<>\"']+")
_TRAILING = ".,;:!?)]}"


def redirect_base() -> str | None:
    """Origem pública HTTPS do site (ex.: https://autoorbital.com.br); sem ela, desligado."""
    value = (os.environ.get("CLICK_REDIRECT_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query:
        return None
    return value


def _token_for(job, target):
    row = query_db(
        """
        INSERT INTO post_link_clicks (token, user_id, profile_id, post_id, publish_job_id, network, target_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (publish_job_id, target_url) DO UPDATE SET target_url = EXCLUDED.target_url
        RETURNING token
        """,
        (secrets.token_urlsafe(16), job["user_id"], job["profile_id"], job["post_id"],
         job["id"], job["network"], target),
        True,
    )
    return row["token"]


def rewrite_text(text, job, base, tokens):
    def swap(match):
        raw = match.group(0)
        url = raw.rstrip(_TRAILING)
        if not is_safe_shopee_link(url):
            return raw
        if url not in tokens:
            tokens[url] = _token_for(job, url)
        return f"{base}/r/{tokens[url]}" + raw[len(url):]
    return _LINK.sub(swap, text)


def rewrite_parts(parts, publish_job_id):
    base = redirect_base()
    if not base or not publish_job_id or not parts:
        return parts
    try:
        job = query_db(
            "SELECT id, user_id, profile_id, post_id, network FROM publish_jobs WHERE id = %s",
            (str(publish_job_id),), True,
        )
        rule = NETWORK_RULES.get(job["network"]) if job else None
        if not rule:
            return parts
        tokens, result = {}, []
        for part in parts:
            text = part.get("text") or ""
            new = rewrite_text(text, job, base, tokens)
            # Link maior não pode estourar o limite da rede: nesse caso mantém o direto.
            fits = text_length(rule, new) <= rule["max_chars"] or text_length(rule, new) <= text_length(rule, text)
            result.append({**part, "text": new if fits else text})
        return result
    except Exception:
        logger.warning("Redirecionador de cliques indisponível; usando o link direto")
        return parts
