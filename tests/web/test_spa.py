"""Testa o catch-all do SPA (web/routes/spa.py).

Sem dependência de Postgres/conftest raiz de propósito: importa o
módulo direto por caminho de arquivo e monta um app Flask isolado, só
com o spa_bp registrado, apontando pra um frontend/dist fake num
diretório temporário.

Regressão coberta: GET /videos/<algo>.mp4 devolvia index.html (bug de
produção) porque só existia rota estática pra /assets/, e qualquer
outro arquivo copiado de frontend/public/ pro topo de frontend/dist/
caía no catch-all de SPA.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from flask import Flask

_SPA_PY = Path(__file__).resolve().parents[2] / "web" / "routes" / "spa.py"


def _load_spa_module():
    spec = importlib.util.spec_from_file_location("_test_spa_module", _SPA_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def spa_app(tmp_path, monkeypatch):
    module = _load_spa_module()

    dist_dir = tmp_path / "dist"
    (dist_dir / "videos").mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html>spa index</html>")
    (dist_dir / "sw.js").write_text("self.skipWaiting()")
    (dist_dir / "videos" / "teste.mp4").write_bytes(b"fake-mp4-bytes")

    monkeypatch.setattr(module, "_DIST_DIR", dist_dir)
    monkeypatch.setattr(module, "_ASSETS_DIR", dist_dir / "assets")

    app = Flask(__name__)
    app.register_blueprint(module.spa_bp)
    app.config.update(TESTING=True)
    return app


def test_serves_real_static_file_outside_assets(spa_app):
    client = spa_app.test_client()

    res = client.get("/videos/teste.mp4")

    assert res.status_code == 200
    assert res.data == b"fake-mp4-bytes"
    assert res.content_type != "text/html; charset=utf-8"


def test_unknown_spa_route_still_falls_back_to_index(spa_app):
    client = spa_app.test_client()

    res = client.get("/alguma-rota-spa-qualquer")

    assert res.status_code == 200
    assert b"spa index" in res.data
    assert res.content_type == "text/html; charset=utf-8"


def test_spa_navigation_html_cannot_be_cached_after_deploy(spa_app):
    client = spa_app.test_client()
    for path in ("/", "/admin/overview", "/index.html"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"


def test_worker_script_cache_is_disabled(spa_app):
    response = spa_app.test_client().get("/sw.js")
    assert response.status_code == 200
    assert response.data == b"self.skipWaiting()"
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"


def test_regular_static_media_does_not_receive_no_store(spa_app):
    response = spa_app.test_client().get("/videos/teste.mp4")
    assert response.status_code == 200
    assert "no-store" not in response.headers.get("Cache-Control", "")


def test_social_preview_declared_in_server_html_and_brand_png():
    """Social bots get metadata from HTML without running JavaScript."""
    import struct
    from html.parser import HTMLParser

    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")

    class Metadata(HTMLParser):
        def __init__(self):
            super().__init__()
            self.meta = {}
            self.links = {}

        def handle_starttag(self, tag, attrs):
            props = dict(attrs)
            if tag == "meta":
                key = props.get("property") or props.get("name")
                if key:
                    self.meta[key] = props.get("content")
            if tag == "link" and props.get("rel"):
                self.links[props["rel"]] = props.get("href")

    parsed = Metadata()
    parsed.feed(html)
    canonical = "https://shopee-bot-fj0w.onrender.com/"
    image_url = canonical + "brand/og-image.png"
    # Sem canonical/og:url estáticos: o mesmo bundle serve staging e produção e o link compartilhado
    # mantém o próprio domínio (frontend/tests/landing-share-metadata.test.mjs fixa o mesmo contrato).
    assert "canonical" not in parsed.links
    assert "og:url" not in parsed.meta
    assert parsed.meta["og:type"] == "website"
    assert parsed.meta["og:locale"] == "pt_BR"
    assert parsed.meta["og:title"] and parsed.meta["og:description"]
    assert parsed.meta["twitter:card"] == "summary_large_image"
    assert parsed.meta["og:image"] == parsed.meta["twitter:image"] == image_url
    assert parsed.meta["og:image:secure_url"] == image_url
    assert parsed.meta["og:image:type"] == "image/png"
    assert parsed.meta["og:image:alt"] and parsed.meta["twitter:image:alt"]
    image_data = (root / "frontend" / "public" / "brand" / "og-image.png").read_bytes()
    assert image_data.startswith(bytes.fromhex("89504e470d0a1a0a"))
    assert struct.unpack(">II", image_data[16:24]) == (1200, 630)
    assert len(image_data) < 600_000


def test_social_assets_are_files_not_spa_fallback(spa_app, tmp_path):
    # A social crawler must receive image/png, not the SPA's text/html fallback.
    module = sys.modules["_test_spa_module"]
    image = module._DIST_DIR / "brand" / "og-image.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"preview")
    response = spa_app.test_client().get("/brand/og-image.png")
    assert response.status_code == 200
    assert response.content_type == "image/png"
    assert response.data.startswith(bytes.fromhex("89504e47"))


def test_hashed_assets_are_cached_for_a_year_and_public_files_for_a_day(spa_app, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(exist_ok=True)
    (dist / "assets" / "index-AbC123.js").write_text("console.log(1)")
    client = spa_app.test_client()

    asset = client.get("/assets/index-AbC123.js")
    assert asset.status_code == 200
    assert asset.headers["Cache-Control"] == "public, max-age=31536000, immutable"

    video = client.get("/videos/teste.mp4")
    assert video.headers["Cache-Control"] == "public, max-age=86400"


def test_service_worker_and_html_remain_uncached(spa_app):
    client = spa_app.test_client()
    for path in ("/sw.js", "/", "/index.html"):
        assert client.get(path).headers["Cache-Control"] == "no-store, no-cache, must-revalidate"


def test_self_hosted_font_is_served_as_a_file_not_as_html(spa_app, tmp_path):
    fonts = tmp_path / "dist" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    (fonts / "mona-sans-latin-wght-normal.woff2").write_bytes(b"wOF2-test")
    response = spa_app.test_client().get("/fonts/mona-sans-latin-wght-normal.woff2")
    assert response.status_code == 200
    assert response.data == b"wOF2-test"
    assert "text/html" not in response.headers["Content-Type"]
    assert response.headers["Cache-Control"] == "public, max-age=86400"
