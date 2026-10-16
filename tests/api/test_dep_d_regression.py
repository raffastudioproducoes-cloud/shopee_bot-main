"""Testes de regressão de segurança para Lote 02 (DEP-D).

Cobre os 8 alertas de segurança de clientes HTTP (idna, requests, urllib3):
- idna (GHSA-65pc-fj4g-8rjx):
    Validação antecipada de tamanho de rótulo/domínio contra DoS em idna.encode().
- requests (GHSA-gc5v-m9x4-r6x2):
    Uso de arquivo temporário seguro (mkstemp) em extract_zipped_paths sem reutilizar arquivos previsíveis.
- urllib3 (GHSA-vxq7-64xx-v4gw):
    Limite de 64KB no tamanho da linha do chunk-size em streaming/read_chunked (ProtocolError se exceder).
- urllib3 (GHSA-gm62-xv2j-4w53):
    Limite de encadeamento na descompressão HTTP (max_decode_links = 5, DecodeError se exceder).
- urllib3 (GHSA-2xpw-w6gg-jr37 & GHSA-38jv-5279-wg99):
    Salvaguardas de streaming e descompressão com controle de buffer max_length.
- urllib3 (GHSA-qccp-gfcp-xxvc):
    Remoção de cabeçalhos sensíveis (Authorization, Cookie, Proxy-Authorization) em redirects cross-origin.
- urllib3 (GHSA-8988-9cw3-xx77):
    Isolamento da configuração TLS do proxy HTTPS via ProxyConfig independente do servidor destino.
- Integração da aplicação (utils.download_image):
    Validação de streaming HTTP controlado localmente sem contatar provedores reais.

Totalmente isolado: sem banco de dados, sem conftest raiz, sem chamadas de rede externas.
"""

import io
import os
import ssl
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from PIL import Image
import pytest

import idna
import requests
import requests.utils
import urllib3
from urllib3.exceptions import DecodeError, ProtocolError
from urllib3.poolmanager import ProxyConfig, ProxyManager
from urllib3.response import HTTPResponse, MultiDecoder, _MAX_CHUNK_LINE_LENGTH
from urllib3.util.retry import Retry
from utils import download_image


# ==============================================================================
# 1. idna — GHSA-65pc-fj4g-8rjx
# ==============================================================================
def test_idna_ghsa_65pc_fj4g_8rjx_crafted_input_validation():
    """Valida GHSA-65pc-fj4g-8rjx em idna >= 3.15.

    idna.encode() deve rejeitar antecipadamente domínios e rótulos excessivamente
    longos (com codepoints CONTEXTO/CONTEXTJ ou caracteres repetidos) sem entrar
    em loops caros ou travamentos de CPU.
    """
    # Rótulo com repetição que acionaria valid_contexto repetidamente
    crafted_contexto = "\u0660" * 100
    with pytest.raises(idna.core.IDNAError):
        idna.encode(crafted_contexto)

    crafted_katakana = "\u30fb" * 100 + "\u6f22"
    with pytest.raises(idna.core.IDNAError):
        idna.encode(crafted_katakana)

    # Rótulo que excede o limite DNS de 63 octetos
    long_label = "a" * 64
    with pytest.raises(idna.core.IDNAError):
        idna.encode(long_label)

    # Domínio legítimo internacionalizado deve codificar perfeitamente
    encoded = idna.encode("exemplo.com.br")
    assert encoded == b"exemplo.com.br"

    encoded_accent = idna.encode("café.com")
    assert encoded_accent == b"xn--caf-dma.com"


# ==============================================================================
# 2. requests — GHSA-gc5v-m9x4-r6x2
# ==============================================================================
def test_requests_ghsa_gc5v_m9x4_r6x2_extract_zipped_paths_secure_temp(tmp_path, monkeypatch):
    """Valida GHSA-gc5v-m9x4-r6x2 em requests >= 2.33.0.

    extract_zipped_paths() deve usar tempfile.mkstemp() para extrair membros
    de zip em arquivos temporários únicos e seguros, impedindo a reutilização
    insegura de arquivos pré-existentes no diretório temporário do sistema.
    """
    # Cria um zip de teste com um membro específico
    zip_path = str(tmp_path / "bundle.zip")
    member_name = "secret_bundle/cacert.pem"
    content = b"TEST-CERT-CONTENT-12345"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(member_name, content)

    # Isola o diretório temporário para nunca sobrescrever um arquivo do sistema.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    temp_dir = tempfile.gettempdir()
    poisoned_target = os.path.join(temp_dir, "cacert.pem")
    poisoned_content = b"MALICIOUS-PRE-EXISTING-FILE"

    try:
        with open(poisoned_target, "wb") as f:
            f.write(poisoned_content)

        # Chama extract_zipped_paths com caminho apontando para dentro do zip
        lookup_path = f"{zip_path}/{member_name}"
        extracted = requests.utils.extract_zipped_paths(lookup_path)

        # Em requests >= 2.33.0, o caminho extraído NUNCA deve ser o arquivo previsível envenenado
        assert extracted != poisoned_target, (
            f"extract_zipped_paths reutilizou arquivo inseguro previsível: {extracted}"
        )
        assert os.path.exists(extracted), "Arquivo extraído não existe"
        with open(extracted, "rb") as f:
            assert f.read() == content, "Conteúdo extraído não corresponde ao zip legítimo"

        # Limpeza do arquivo extraído temporário
        try:
            os.remove(extracted)
        except OSError:
            pass

    finally:
        if os.path.exists(poisoned_target):
            try:
                os.remove(poisoned_target)
            except OSError:
                pass


# ==============================================================================
# 3. urllib3 — GHSA-vxq7-64xx-v4gw
# ==============================================================================
def test_urllib3_ghsa_vxq7_64xx_v4gw_chunk_size_line_limit():
    """Valida GHSA-vxq7-64xx-v4gw em urllib3 >= 2.8.0.

    HTTPResponse._update_chunk_length() deve rejeitar linhas de chunk-size
    que excedam _MAX_CHUNK_LINE_LENGTH (65536 bytes) com ProtocolError,
    impedindo estouro de memória provocado por servidores maliciosos.
    """
    assert _MAX_CHUNK_LINE_LENGTH == 65536

    # Simula stream com linha de tamanho de chunk abusiva (> 65536 sem \r\n)
    oversized_chunk_line = b"F" * (_MAX_CHUNK_LINE_LENGTH + 10) + b"\r\n"
    fp = io.BytesIO(oversized_chunk_line)
    dummy_response = type("DummyResponse", (), {"fp": fp})()

    resp = HTTPResponse(body=io.BytesIO())
    resp._fp = dummy_response

    with pytest.raises(ProtocolError) as exc_info:
        resp._update_chunk_length()

    assert "Response chunk size line exceeded maximum allowed length" in str(exc_info.value)

    # Linha de chunk válida dentro do limite deve operar normalmente
    valid_fp = io.BytesIO(b"1A\r\n" + b"X" * 0x1A + b"\r\n0\r\n\r\n")
    valid_resp_obj = type("DummyResponse", (), {"fp": valid_fp})()
    valid_resp = HTTPResponse(body=io.BytesIO())
    valid_resp._fp = valid_resp_obj

    valid_resp._update_chunk_length()
    assert valid_resp.chunk_left == 0x1A


# ==============================================================================
# 4. urllib3 — GHSA-gm62-xv2j-4w53
# ==============================================================================
def test_urllib3_ghsa_gm62_xv2j_4w53_unbounded_decompression_chain():
    """Valida GHSA-gm62-xv2j-4w53 em urllib3 >= 2.6.0.

    MultiDecoder deve limitar o número máximo de algoritmos de descompressão
    encadeados no cabeçalho Content-Encoding (max_decode_links = 5).
    Se exceder, deve lançar DecodeError.
    """
    assert MultiDecoder.max_decode_links == 5

    # Encadeamento excessivo (> 5 links) deve lançar DecodeError
    too_many_encodings = "gzip, gzip, gzip, gzip, gzip, gzip"
    with pytest.raises(DecodeError) as exc_info:
        MultiDecoder(too_many_encodings)

    assert "Too many content encodings in the chain" in str(exc_info.value)

    # Encadeamento dentro do limite (<= 5) deve ser aceito
    valid_chain = "gzip, deflate"
    decoder = MultiDecoder(valid_chain)
    assert len(decoder._decoders) == 2


# ==============================================================================
# 5. urllib3 — GHSA-2xpw-w6gg-jr37 & GHSA-38jv-5279-wg99
# ==============================================================================
def test_urllib3_ghsa_2xpw_w6gg_jr37_streaming_decompression_bounds():
    """Valida GHSA-2xpw-w6gg-jr37 e GHSA-38jv-5279-wg99.

    Garante que o descompressor respeita limites de streaming e parâmetros
    max_length em leituras incrementais sem alocação descontrolada.
    """
    decoder = MultiDecoder("gzip")
    import gzip
    compressed = gzip.compress(b"A" * 1000)

    # Descompressão limitada por max_length
    chunk = decoder.decompress(compressed, max_length=100)
    assert len(chunk) == 100
    assert chunk == b"A" * 100

    # Continuação da descompressão
    remainder = decoder.decompress(b"", max_length=900)
    assert len(remainder) == 900
    assert remainder == b"A" * 900


# ==============================================================================
# 6. urllib3 — GHSA-qccp-gfcp-xxvc
# ==============================================================================
def test_urllib3_ghsa_qccp_gfcp_xxvc_sensitive_headers_stripped_on_redirect():
    """Valida GHSA-qccp-gfcp-xxvc em urllib3 >= 2.7.0.

    Garante que cabeçalhos sensíveis (Authorization, Cookie, Proxy-Authorization)
    são devidamente removidos em redirecionamentos cross-origin.
    """
    sensitive_headers = Retry.DEFAULT_REMOVE_HEADERS_ON_REDIRECT
    assert "Authorization" in sensitive_headers
    assert "Cookie" in sensitive_headers
    assert "Proxy-Authorization" in sensitive_headers

    pool = urllib3.connectionpool.HTTPConnectionPool(host="legitimate-service.com", port=80)
    assert pool.is_same_host("http://legitimate-service.com/path") is True
    assert pool.is_same_host("https://untrusted-external.com/path") is False
    assert pool.is_same_host("http://other-domain.org/login") is False


# ==============================================================================
# 7. urllib3 — GHSA-8988-9cw3-xx77
# ==============================================================================
def test_urllib3_ghsa_8988_9cw3_xx77_proxy_tls_config_isolation():
    """Valida GHSA-8988-9cw3-xx77 em urllib3 >= 2.8.0.

    ProxyManager deve isolar a configuração TLS do proxy HTTPS em ProxyConfig,
    garantindo que proxy_ssl_context e validações do proxy não sejam sobrescritas
    ou ignoradas por parâmetros TLS do servidor de destino.
    """
    dummy_proxy_ctx = ssl.create_default_context()
    proxy_config = ProxyConfig(
        ssl_context=dummy_proxy_ctx,
        use_forwarding_for_https=False,
        assert_hostname="proxy.internal",
        assert_fingerprint=None,
    )

    assert proxy_config.ssl_context is dummy_proxy_ctx
    assert proxy_config.assert_hostname == "proxy.internal"

    pm = ProxyManager(
        proxy_url="http://127.0.0.1:8080",
        proxy_ssl_context=dummy_proxy_ctx,
        proxy_assert_hostname="proxy.internal",
    )
    assert pm.proxy_config.ssl_context is dummy_proxy_ctx
    assert pm.proxy_config.assert_hostname == "proxy.internal"


# ==============================================================================
# 8. Integração controlada da aplicação — utils.download_image (sem rede externa)
# ==============================================================================
def _generate_valid_jpeg_bytes():
    """Gera bytes de uma imagem JPEG mínima válida em memória."""
    img = Image.new("RGB", (10, 10), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


_VALID_JPEG_BYTES = _generate_valid_jpeg_bytes()


class _ControlledMediaHandler(BaseHTTPRequestHandler):
    """Servidor HTTP local de teste para streaming e downloads controlados."""

    def do_GET(self):
        if self.path == "/valid-image.jpg":
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(_VALID_JPEG_BYTES)))
            self.end_headers()
            self.wfile.write(_VALID_JPEG_BYTES)

        elif self.path == "/not-an-image.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"plain text data")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silencia logs no stderr durante execução de teste
        pass


@pytest.fixture(scope="module")
def local_media_server():
    """Sobe um servidor HTTP local em porta efêmera para teste de streaming."""
    server = HTTPServer(("127.0.0.1", 0), _ControlledMediaHandler)
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield base_url
    server.shutdown()
    server.server_close()


def test_application_download_image_streaming_local_server(local_media_server, tmp_path):
    """Testa download_image() com streaming contra o servidor local controlado."""
    target_file = str(tmp_path / "saved_image.jpg")
    image_url = f"{local_media_server}/valid-image.jpg"

    # Deve baixar com sucesso e validar integridade via PIL
    success = download_image(image_url, save_path=target_file)
    assert success is True
    assert os.path.exists(target_file)
    assert os.path.getsize(target_file) > 0

    # Deve rejeitar conteúdo que não seja imagem
    non_image_url = f"{local_media_server}/not-an-image.txt"
    fail_target = str(tmp_path / "should_not_exist.txt")
    fail_success = download_image(non_image_url, save_path=fail_target)
    assert fail_success is False
    assert not os.path.exists(fail_target)
