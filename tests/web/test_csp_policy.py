import os
import sys
import tempfile
import types
from pathlib import Path

os.environ.setdefault("FLASK_MAX_CONTENT_LENGTH", "52428800")
os.environ.setdefault("FLASK_SESSION_SECRET", "test_only_secret")
os.environ.setdefault("FLASK_UPLOAD_FOLDER", tempfile.gettempdir())
os.environ.setdefault("FLASK_DEBUG", "False")

project_root = Path(__file__).resolve().parents[2]
if "shopee_bot" not in sys.modules:
    package = types.ModuleType("shopee_bot")
    package.__path__ = [str(project_root)]
    sys.modules["shopee_bot"] = package

from shopee_bot.web import DEBUG, app


def test_false_debug_value_does_not_enable_debug_mode():
    assert DEBUG is False


def test_csp_does_not_allow_dynamic_code_execution():
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert "'unsafe-eval'" not in response.headers["Content-Security-Policy"]


def test_non_template_health_route_blocks_inline_scripts():
    with app.test_client() as client:
        response = client.get("/health")
    script_src = response.headers["Content-Security-Policy"].split("script-src ", 1)[1].split(";", 1)[0]
    assert "'unsafe-inline'" not in script_src


def test_spa_csp_blocks_inline_scripts():
    with app.test_client() as client:
        response = client.get("/")
    policy = response.headers["Content-Security-Policy"]
    assert "script-src 'self';" in policy
    assert "'unsafe-inline'" not in policy.split("script-src ", 1)[1].split(";", 1)[0]


def test_spa_startup_has_no_inline_script_or_handler():
    html = (project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "onclick=" not in html
    assert 'src="/splash.js"' in html


def test_spa_has_no_inline_style_elements():
    html = (project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "<style" not in html.lower()
    assert 'href="/splash.css"' in html
    assert (project_root / "frontend" / "public" / "splash.css").is_file()


def test_react_pages_externalize_literal_style_elements():
    pages = (
        ("src/components/layout/AppFooter.tsx", "src/components/layout/AppFooter.css"),
        ("src/pages/LoginPage.tsx", "src/pages/LoginPage.css"),
        ("src/pages/legal/LegalLayout.tsx", "src/pages/legal/LegalLayout.css"),
    )
    for component, css in pages:
        source = (project_root / "frontend" / component).read_text(encoding="utf-8")
        assert "<style" not in source.lower(), component
        assert (project_root / "frontend" / css).is_file(), css


def test_login_page_has_no_inline_style_attributes():
    source = (project_root / "frontend" / "src" / "pages" / "LoginPage.tsx").read_text(encoding="utf-8")
    assert "style=" not in source


def test_spa_forbids_inline_style_elements_while_legacy_is_unmodified():
    with app.test_client() as client:
        spa_policy = client.get("/").headers["Content-Security-Policy"]
        health_policy = client.get("/health").headers["Content-Security-Policy"]
    assert "style-src-elem 'self' https://fonts.googleapis.com;" in spa_policy
    assert "style-src-elem" not in health_policy


def test_legal_layout_has_no_inline_style_attributes():
    source = (project_root / "frontend" / "src" / "pages" / "legal" / "LegalLayout.tsx").read_text(encoding="utf-8")
    assert "style=" not in source


def test_generated_stylesheet_covers_all_static_csp_classes():
    import re
    style_root = project_root / "frontend" / "src"
    stylesheet = (style_root / "styles" / "csp-static-generated.css").read_text(encoding="utf-8")
    declared = set(re.findall(r"\.((?:csp-s-)\d{4})\s*\{", stylesheet))
    referenced = set()
    for component in style_root.rglob("*.tsx"):
        referenced.update(re.findall(r"className=\"((?:csp-s-)\d{4})\"", component.read_text(encoding="utf-8")))
    assert len(declared) >= 399
    assert declared == referenced, "Cada classe CSP estatica deve existir no CSS e ser usada no JSX"


def test_spa_style_policy_omits_unsafe_inline_and_blocks_html_style_attributes():
    with app.test_client() as client:
        policy = client.get("/").headers["Content-Security-Policy"]
    assert "style-src 'self' https://fonts.googleapis.com;" in policy
    assert "style-src-elem 'self' https://fonts.googleapis.com;" in policy
    assert "style-src-attr 'none';" in policy
    assert "'unsafe-inline'" not in policy


def test_default_security_policy_blocks_inline_styles_when_legacy_is_disabled():
    with app.test_client() as client:
        policy = client.get("/health").headers["Content-Security-Policy"]
    assert "style-src 'self' https://fonts.googleapis.com;" in policy
    assert "'unsafe-inline'" not in policy


def test_unauthenticated_reserved_routes_return_404_instead_of_internal_server_error():
    with app.test_client() as client:
        for path in ("/api/", "/internal/", "/static/missing-security-probe.txt"):
            response = client.get(path)
            assert response.status_code == 404, path
            assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_method_not_allowed_stays_405():
    with app.test_client() as client:
        response = client.get("/internal/scheduler/jobs")
    assert response.status_code == 405


def test_spa_csp_defines_fallbackless_protective_directives():
    with app.test_client() as client:
        policy = client.get("/").headers["Content-Security-Policy"]
    assert "base-uri 'none';" in policy
    assert "form-action 'self';" in policy
    assert "object-src 'none'" in policy
