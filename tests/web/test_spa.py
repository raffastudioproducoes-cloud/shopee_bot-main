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
