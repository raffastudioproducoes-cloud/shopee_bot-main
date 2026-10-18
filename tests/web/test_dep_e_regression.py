"""Testes de regressão de segurança para Lote 01 (DEP-E).

Cobre os 6 alertas de segurança de dependências de infraestrutura:
- Werkzeug (GHSA-29vq-49wr-vm6x, GHSA-87hc-h4r5-73f7, GHSA-g6x2-hccm-hh4m, GHSA-hgf8-39gv-g3f2):
  Bloqueio de nomes especiais de dispositivos Windows em safe_join() e send_from_directory().
- Flask (GHSA-68rp-wp8r-4726):
  Garantia de que acessos ao objeto session (inclusive operador 'in') definem o cabeçalho 'Vary: Cookie'.
- python-dotenv (GHSA-mf9w-mj56-hr94):
  Garantia de que set_key possui follow_symlinks=False por padrão e load_dotenv opera normalmente.

Totalmente isolado: sem banco de dados, sem conftest raiz, sem rede.
"""

import inspect
import io
import os
import pytest

from flask import Flask, session, send_from_directory
from werkzeug.security import safe_join
from dotenv import set_key, load_dotenv


@pytest.mark.skipif(os.name != "nt", reason="Nomes de dispositivos são exclusivos do Windows")
def test_werkzeug_safe_join_blocks_windows_device_names():
    """Valida GHSA-29vq-49wr-vm6x, GHSA-87hc-h4r5-73f7, GHSA-g6x2-hccm-hh4m, GHSA-hgf8-39gv-g3f2.

    safe_join deve retornar None para nomes reservados do Windows, extensões
    compostas e variações de caixa, permitindo arquivos legítimos.
    """
    base = "C:/fake_base" if os.name == "nt" else "/fake_base"

    # Nomes especiais do Windows que em versões vulneráveis (< 3.1.9) retornavam caminhos válidos
    dangerous_names = [
        "nul",
        "NUL",
        "con",
        "CON",
        "aux",
        "AUX",
        "prn",
        "PRN",
        "com1",
        "COM1",
        "lpt1",
        "LPT1",
        "nul.txt",
        "NUL.TXT",
        "aux.tar.gz",
        "con.log",
    ]

    for name in dangerous_names:
        result = safe_join(base, name)
        assert result is None, f"safe_join não bloqueou o dispositivo Windows perigoso: {name!r} (retornou {result!r})"

    # Caminhos legítimos devem ser permitidos normalmente
    assert safe_join(base, "style.css") is not None
    assert safe_join(base, "sub/folder/file.js") is not None


def test_flask_session_adds_vary_cookie_header():
    """Valida GHSA-68rp-wp8r-4726.

    Acessar o objeto session através do operador 'in' deve definir o cabeçalho
    'Vary: Cookie' na resposta para impedir cache indevido por proxies reversos.
    """
    app = Flask(__name__)
    app.secret_key = "test-isolated-secret-key"
    app.config.update(TESTING=True)

    @app.route("/check-session-in")
    def check_session_in():
        # Acesso via operador 'in' (não muta a sessão e não acessa valores diretamente)
        _ = "user_id" in session
        return "ok"

    @app.route("/check-session-get")
    def check_session_get():
        _ = session.get("user_id")
        return "ok"

    with app.test_client() as client:
        res_in = client.get("/check-session-in")
        assert res_in.status_code == 200
        vary_in = res_in.headers.get("Vary", "")
        assert "Cookie" in vary_in, f"Vary header esperado contendo Cookie, obtido: {vary_in!r}"

        res_get = client.get("/check-session-get")
        assert res_get.status_code == 200
        vary_get = res_get.headers.get("Vary", "")
        assert "Cookie" in vary_get, f"Vary header esperado contendo Cookie, obtido: {vary_get!r}"


def test_python_dotenv_set_key_safe_symlink_defaults():
    """Valida GHSA-mf9w-mj56-hr94.

    Verifica que set_key possui o parâmetro follow_symlinks com default False,
    mitigando sobrescrita arbitrária de arquivos via links simbólicos.
    """
    sig = inspect.signature(set_key)
    assert "follow_symlinks" in sig.parameters, "Parâmetro follow_symlinks ausente em dotenv.set_key"
    assert sig.parameters["follow_symlinks"].default is False, "Default de follow_symlinks em set_key deve ser False"


def test_python_dotenv_load_dotenv_stream(monkeypatch):
    """Verifica compatibilidade e funcionamento de load_dotenv com a versão atualizada."""
    monkeypatch.delenv("TEST_DOTENV_DEP_E", raising=False)
    fake_env = io.StringIO("TEST_DOTENV_DEP_E=updated_value_ok\n")
    loaded = load_dotenv(stream=fake_env)
    assert loaded is True
    assert os.environ.get("TEST_DOTENV_DEP_E") == "updated_value_ok"


@pytest.mark.skipif(os.name != "nt", reason="Nomes de dispositivos são exclusivos do Windows")
def test_flask_send_from_directory_windows_device_names(tmp_path):
    """Valida contenção ponta-a-ponta via Flask send_from_directory com Werkzeug safe_join."""
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "valid.txt").write_text("conteudo seguro")

    app = Flask(__name__)
    app.config.update(TESTING=True)

    @app.route("/media/<path:filename>")
    def get_media(filename):
        return send_from_directory(str(media_dir), filename)

    with app.test_client() as client:
        # Arquivo válido
        res_valid = client.get("/media/valid.txt")
        assert res_valid.status_code == 200
        assert res_valid.data == b"conteudo seguro"

        # Dispositivo perigoso no Windows deve resultar em 404 (NotFound via safe_join retornando None)
        res_nul = client.get("/media/nul")
        assert res_nul.status_code == 404

        res_aux = client.get("/media/aux.tar.gz")
        assert res_aux.status_code == 404
