import json
import os
import re
from flask import request
from urllib.parse import urlparse, urljoin


# only within app context
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def is_url_for(url, domain):
    """domain = without .www"""
    domain_parsed = urlparse(domain)
    re_domain = re.compile(f"^(www\\.)?{domain_parsed.netloc}$")
    try:
        url_parsed = urlparse(url)
        return url_parsed.scheme == domain_parsed.scheme \
            and re_domain.search(url_parsed.netloc) is not None
    except Exception:
        return False


def cors_origins():
    """Origens liberadas pro CORS do Flask: CORS_ORIGINS (mesmo formato
    JSON que o pydantic de api/config.py aceita, ou lista separada por
    vírgula) + FRONTEND_URL. Vazio = sem CORS (o SPA é servido pelo próprio
    Flask, mesma origem, e não precisa)."""
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    try:
        origins = json.loads(raw) if raw.startswith("[") else raw.split(",")
    except ValueError:
        origins = []
    origins.append(os.environ.get("FRONTEND_URL", ""))
    return sorted({o.strip().rstrip("/") for o in origins if isinstance(o, str) and o.strip()})
