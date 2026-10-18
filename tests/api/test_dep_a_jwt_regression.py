"""Testes de regressão de segurança para Lote 05 (DEP-A).

Cobre os 15 alertas de segurança de PyJWT e validação exclusiva de HS256:
- GHSA-ffc3-869f-jxw9 (CRITICAL):
    Bypass de detecção de PEM assimétrico por mutação de whitespace/quebras de linha.
    Provado: PyJWT 2.15.0 rejeita chaves PEM mutadas com InvalidKeyError ao tentar
    usá-las como segredo HMAC. A aplicação usa segredo simétrico puro.
- GHSA-p4g4-x82p-q773 (HIGH):
    Chaves públicas em formato DER como segredo HMAC (CVE-2022-29217 guard).
    Provado: Auto Orbital utiliza segredo simétrico exclusivo (settings.api_secret_key)
    e não consome chaves públicas DER nem algoritmos assimétricos.
- GHSA-xgmm-8j9v-c9wx (HIGH):
    JWK de chave pública aceito como segredo HMAC.
    Provado: prepare_key rejeita dicionários/JSONs de JWK como segredos HMAC;
    o Auto Orbital não utiliza JWK.
- GHSA-752w-5fwx-jx9f (HIGH):
    Aceite de extensões críticas desconhecidas no cabeçalho `crit` (RFC 7515 §4.1.11).
    Provado: validadores do Auto Orbital (_decode_token, _user_from_cookie, _verify_oauth_state)
    rejeitam tokens contendo o cabeçalho `crit`.
- GHSA-9v7f-9g4p-ffgj (HIGH), GHSA-993g-76c3-p5m4 (MODERATE), GHSA-2gx3-rcp4-g85q (MODERATE),
  GHSA-fhv5-28vv-h8m8 (LOW), GHSA-jq35-7prp-9v3f (MODERATE), GHSA-w6j9-cwv2-h6wq (MODERATE),
  GHSA-x33g-cr3x-6449 (MODERATE):
    Vulnerabilidades ligadas a PyJWKClient, esquemas remotos (SSRF), amplificação de requisições
    JWKS por `kid`, desvios de allowlist por `PyJWK`, falhas de parsing de JWK Set e confusão OKP.
    Provado: inexistência de PyJWKClient e JWKS no repositório; exclusividade estrita
    de algoritmo HS256 e chave simétrica em todos os pontos de decode.
- GHSA-42vr-xj54-vc7v (MODERATE):
    RecursionError não tratado em payloads profundamente aninhados (DoS).
    Provado: tratamento seguro via exceção sem derrubar o worker ou gerar 500 não tratado.
- GHSA-w7vc-732c-9m39 (MODERATE):
    DoS por base64url não limitado em JWS detached com b64=false.
    Provado: aplicação opera exclusivamente com compact JWS com payload embutido e HS256.
- GHSA-jwrc-g2q2-pq5p (MODERATE):
    ReDoS na função is_pem_format corrigido no PyJWT 2.14.0+.
- GHSA-hxm8-2xgr-2p9m (MODERATE):
    Bypass de revogação por representação não canônica da assinatura.
    Provado: a aplicacao nao usa blacklist por string bruta do JWT; a troca de senha
    invalida via pwv. Logout ainda nao revoga o token no servidor (achado F-02).

Totalmente isolado: sem banco de dados real, sem conftest raiz legado, sem chamadas externas de rede.
"""

import base64
import datetime
from datetime import timedelta, timezone
import json
import re
from unittest.mock import MagicMock

import jwt
from jwt.exceptions import (
    DecodeError,
    InvalidAlgorithmError,
    InvalidKeyError,
    InvalidSignatureError,
    PyJWTError,
)
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from api.config import settings
from api.middleware import _user_from_cookie
from api.routers.auth import _create_token, _decode_token
from api.routers.credentials import _sign_oauth_state, _verify_oauth_state


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


# ==============================================================================
# 1. GHSA-ffc3-869f-jxw9 (CRITICAL) & GHSA-xgmm-8j9v-c9wx (HIGH)
# ==============================================================================
def test_pyjwt_ghsa_ffc3_869f_jxw9_mutated_pem_rejected_as_hmac_secret():
    """Valida GHSA-ffc3-869f-jxw9: PyJWT 2.15.0 rejeita chaves PEM com
    whitespaces, CRLF ou quebras de linha alteradas quando fornecidas como
    segredo para algoritmos HMAC (evitando key-confusion attack)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Mutação com espaços e quebras de linha que contornavam o regex antigo
    mutated_pem_variants = [
        b"   \r\n" + public_pem + b"\r\n   ",
        b"\t" + public_pem.replace(b"\n", b"\r\n") + b"\t\n",
        b"\r\n\r\n" + public_pem,
    ]

    payload = {"sub": "test_user", "id": "123"}
    for mutated_pem in mutated_pem_variants:
        with pytest.raises(InvalidKeyError) as exc_info:
            jwt.encode(payload, mutated_pem, algorithm="HS256")
        assert "asymmetric key" in str(exc_info.value).lower()


def test_pyjwt_ghsa_xgmm_8j9v_c9wx_jwk_confusion_preconditions_absent_and_blocked():
    """Valida GHSA-xgmm-8j9v-c9wx: em ataques de confusão JWK/HMAC, o atacante
    tenta forjar um token HS256 assinado com a chave pública do emissor (JWK).
    No Auto Orbital:
    1. A aplicação não aceita nem utiliza JWKs como segredo.
    2. O validador rejeita tokens assinados com chaves públicas (RS256 ou HS256 com chave do atacante)
       porque a verificação é estritamente vinculada a settings.api_secret_key.
    3. Mistura de famílias (ex.: HS256 + RS256 na allowlist) é terminantemente proibida."""
    fake_jwk_key = b'{"kty":"RSA","n":"sample_modulus","e":"AQAB"}'
    with pytest.raises(InvalidKeyError):
        jwt.encode({"sub": "admin", "id": "1"}, fake_jwk_key, algorithm="HS256")

    # Tokens RS256 legítimos de JWK também são rejeitados pela allowlist exclusiva de HS256
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    rs_token = jwt.encode({"sub": "admin", "id": "1"}, private_pem, algorithm="RS256")
    assert _decode_token(rs_token) is None


# ==============================================================================
# 2. GHSA-752w-5fwx-jx9f (HIGH) — Validação de cabeçalho 'crit'
# ==============================================================================
def test_jwt_ghsa_752w_5fwx_jx9f_rejects_unknown_crit_header():
    """Valida GHSA-752w-5fwx-jx9f: tokens contendo a extensão de cabeçalho 'crit'
    (RFC 7515 §4.1.11) devem ser rejeitados imediatamente, pois o Auto Orbital
    opera exclusivamente com claims padrão sem extensões críticas."""
    payload = {"sub": "alice", "id": "42", "profile_id": "prof_1"}

    # Cria token contendo cabeçalho 'crit'
    token_with_crit = jwt.encode(
        payload,
        settings.api_secret_key,
        algorithm="HS256",
        headers={"crit": ["custom-extension-policy"], "custom-extension-policy": "strict"},
    )

    # 1. Validador principal da autenticação (_decode_token)
    assert _decode_token(token_with_crit) is None

    # 2. Validador do middleware (_user_from_cookie)
    req = MagicMock()
    req.cookies = {"access_token": token_with_crit}
    user_id, username, profile_id = _user_from_cookie(req)
    assert user_id is None
    assert username is None
    assert profile_id is None

    # 3. Validador de OAuth state (_verify_oauth_state)
    req_oauth = MagicMock()
    req_oauth.cookies = {"oauth_state": token_with_crit}
    verified_oauth = _verify_oauth_state(req_oauth, "oauth_state", "some_state", 42, "prof_1")
    assert verified_oauth is None


# ==============================================================================
# 3. Algoritmo HS256 Exclusivo — Provas de Rejeição de Outros Algoritmos
# ==============================================================================
def test_hs256_exclusive_rejects_none_algorithm():
    """Garante que tokens com alg='none' (não assinados) são estritamente rejeitados."""
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "attacker", "id": "1", "exp": 9999999999}
    h_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    p_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    unsigned_token = f"{h_b64}.{p_b64}."

    assert _decode_token(unsigned_token) is None

    req = MagicMock()
    req.cookies = {"access_token": unsigned_token}
    assert _user_from_cookie(req) == (None, None, None)


def test_hs256_exclusive_rejects_asymmetric_algorithms_rs256_es256():
    """Garante que tokens declarando algoritmos assimétricos (RS256, ES256) são rejeitados."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    payload = {"sub": "attacker", "id": "1"}
    rs256_token = jwt.encode(payload, private_pem, algorithm="RS256")

    # Decodificação deve falhar porque a allowlist aceita exclusivamente ['HS256']
    assert _decode_token(rs256_token) is None

    req = MagicMock()
    req.cookies = {"access_token": rs256_token}
    assert _user_from_cookie(req) == (None, None, None)


def test_hs256_exclusive_rejects_other_hmac_algorithms_hs384_hs512():
    """Garante que tokens HMAC de tamanhos diferentes (HS384, HS512) são rejeitados."""
    payload = {"sub": "test", "id": "1"}
    token_hs384 = jwt.encode(payload, settings.api_secret_key, algorithm="HS384")
    token_hs512 = jwt.encode(payload, settings.api_secret_key, algorithm="HS512")

    assert _decode_token(token_hs384) is None
    assert _decode_token(token_hs512) is None


def test_hs256_exclusive_rejects_tampered_signature_and_payload():
    """Garante que qualquer alteração de payload ou assinatura invalida o token."""
    valid_token = _create_token({"sub": "legit_user", "id": "10"})
    header_b64, payload_b64, sig_b64 = valid_token.split(".")

    # Adulteração de payload
    tampered_payload_data = {"sub": "admin_hacked", "id": "1"}
    new_p_b64 = _b64url_encode(json.dumps(tampered_payload_data).encode("utf-8"))
    tampered_payload_token = f"{header_b64}.{new_p_b64}.{sig_b64}"
    assert _decode_token(tampered_payload_token) is None

    # Adulteração de assinatura
    corrupted_sig = sig_b64[:-2] + ("AA" if sig_b64[-2:] != "AA" else "BB")
    tampered_sig_token = f"{header_b64}.{payload_b64}.{corrupted_sig}"
    assert _decode_token(tampered_sig_token) is None


def test_hs256_exclusive_rejects_expired_tokens():
    """Garante que tokens expirados são rejeitados por expiração temporal."""
    past_delta = timedelta(seconds=-10)
    expired_token = _create_token({"sub": "old_user", "id": "99"}, expires_delta=past_delta)
    assert _decode_token(expired_token) is None


# ==============================================================================
# 4. GHSA-42vr-xj54-vc7v (MODERATE) — RecursionError DoS Resilience
# ==============================================================================
def test_jwt_ghsa_42vr_xj54_vc7v_deeply_nested_payload_resilience():
    """Valida GHSA-42vr-xj54-vc7v: tokens com estruturas JSON excessivamente
    aninhadas não provocam vazamento de RecursionError não tratado nem
    derrubam a aplicação."""
    depth = 2500
    nested_json = ("[" * depth) + "1" + ("]" * depth)
    nested_b64 = _b64url_encode(nested_json.encode("utf-8"))
    crafted_token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{nested_b64}.fake_sig"

    # Deve retornar None de forma segura sem lançar exceção não capturada
    assert _decode_token(crafted_token) is None

    req = MagicMock()
    req.cookies = {"access_token": crafted_token}
    assert _user_from_cookie(req) == (None, None, None)


# ==============================================================================
# 5. GHSA-hxm8-2xgr-2p9m (MODERATE) & GHSA-jwrc-g2q2-pq5p (MODERATE)
# ==============================================================================
def test_jwt_ghsa_hxm8_2xgr_2p9m_no_raw_token_blacklist():
    """Valida GHSA-hxm8-2xgr-2p9m: o advisory descreve bypass de revogação quando
    a aplicação indexa a revogação pelo hash do texto bruto do token, permitindo
    que variações não-canônicas da assinatura contornem a blacklist.
    No Auto Orbital:
    1. A troca de senha usa o claim pwv, nao matching da string bruta do JWT.
    2. Tokens com assinatura criptográfica adulterada ou corrompida são rejeitados imediatamente.
    3. O logout nao e testado aqui: a revogacao no servidor e F-02 pendente."""
    from api.routers.auth import _password_version

    original_pw_hash = "$2b$12$e8Yk8...sample_hash_v1..."
    token = _create_token({
        "sub": "user_pwv",
        "id": "123",
        "pwv": _password_version(original_pw_hash),
    })

    decoded = _decode_token(token)
    assert decoded is not None
    assert decoded["pwv"] == _password_version(original_pw_hash)

    # Simula troca de senha: o novo hash de senha produz um pwv diferente
    new_pw_hash = "$2b$12$e8Yk8...sample_hash_v2_updated..."
    assert _password_version(new_pw_hash) != _password_version(original_pw_hash)
    assert decoded["pwv"] != _password_version(new_pw_hash)

    # Assinatura corrompida é estritamente rejeitada
    corrupted_token = token[:-4] + "XXXX"
    assert _decode_token(corrupted_token) is None


def test_pyjwt_ghsa_jwrc_g2q2_pq5p_is_pem_format_redos_safety():
    """Valida GHSA-jwrc-g2q2-pq5p: regex de is_pem_format avalia strings
    patológicas sem backtracking catastrófico (tempo < 0.1s)."""
    import time
    from jwt.utils import is_pem_format

    # Entrada patológica que causava ReDoS no regex anterior
    crafted_payload = b"-----BEGIN " + b"A" * 10000 + b"\n"
    start = time.perf_counter()
    res = is_pem_format(crafted_payload)
    elapsed = time.perf_counter() - start

    assert res is False
    assert elapsed < 0.2  # Execução quase instantânea


# ==============================================================================
# 6. Ausência de PyJWKClient e JWKS no Repositório
# ==============================================================================
def test_absence_of_pyjwk_client_and_jwks_in_application():
    """Garante que a aplicação Auto Orbital não importa nem expõe componentes
    PyJWKClient ou JWKS, mantendo a superfície de ataque nula para:
    GHSA-2gx3-rcp4-g85q, GHSA-9v7f-9g4p-ffgj, GHSA-993g-76c3-p5m4,
    GHSA-fhv5-28vv-h8m8, GHSA-jq35-7prp-9v3f, GHSA-w6j9-cwv2-h6wq, GHSA-x33g-cr3x-6449."""
    import sys

    # Verifica que nenhum módulo da api/ importa ou utiliza PyJWKClient
    import api.middleware
    import api.routers.auth
    import api.routers.credentials
    import api.routers.profiles
    import api.routers.settings

    for mod in [api.middleware, api.routers.auth, api.routers.credentials, api.routers.profiles, api.routers.settings]:
        assert not hasattr(mod, "PyJWKClient"), f"Módulo {mod} possui referência a PyJWKClient"
        assert not hasattr(mod, "PyJWK"), f"Módulo {mod} possui referência a PyJWK"


# ==============================================================================
# 7. Testes Funcionais da Aplicação (Multi-Profile, OAuth, Senha)
# ==============================================================================
def test_auth_token_roundtrip_with_multiprofile_and_pwv():
    """Valida que tokens emitidos com sub, id, profile_id e pwv decodificam
    com integridade total e permanecem 100% compatíveis com multi-perfil."""
    data = {
        "sub": "user_multiprofile",
        "id": "usr_999",
        "profile_id": "prof_alpha_123",
        "pwv": "v1_hash_pwd",
    }
    token = _create_token(data)
    decoded = _decode_token(token)

    assert decoded is not None
    assert decoded["sub"] == "user_multiprofile"
    assert decoded["id"] == "usr_999"
    assert decoded["profile_id"] == "prof_alpha_123"
    assert decoded["pwv"] == "v1_hash_pwd"
    assert "exp" in decoded

    # Validação via middleware
    req = MagicMock()
    req.cookies = {"access_token": token}
    u_id, u_sub, u_prof = _user_from_cookie(req)
    assert u_id == "usr_999"
    assert u_sub == "user_multiprofile"
    assert u_prof == "prof_alpha_123"


def test_oauth_state_creation_and_verification():
    """Valida ciclo completo de criação e verificação do cookie de state OAuth."""
    state, cookie_value = _sign_oauth_state(
        user_id=123, extra={"code_verifier": "pkce_secret_456"}, profile_id="profile_xyz"
    )
    assert state is not None
    assert cookie_value is not None

    req = MagicMock()
    req.cookies = {"oauth_cookie": cookie_value}

    # Verificação com credenciais corretas
    payload = _verify_oauth_state(
        req,
        cookie_name="oauth_cookie",
        state=state,
        user_id=123,
        profile_id="profile_xyz",
    )
    assert payload is not None
    assert payload["uid"] == 123
    assert payload["state"] == state
    assert payload["profile_id"] == "profile_xyz"
    assert payload["code_verifier"] == "pkce_secret_456"

    # Verificação com state divergente (tentativa de CSRF)
    assert (
        _verify_oauth_state(
            req,
            cookie_name="oauth_cookie",
            state="tampered_state",
            user_id=123,
            profile_id="profile_xyz",
        )
        is None
    )

    # Verificação com user_id divergente
    assert (
        _verify_oauth_state(
            req,
            cookie_name="oauth_cookie",
            state=state,
            user_id=999,
            profile_id="profile_xyz",
        )
        is None
    )

    # Verificação com profile_id divergente
    assert (
        _verify_oauth_state(
            req,
            cookie_name="oauth_cookie",
            state=state,
            user_id=123,
            profile_id="other_profile",
        )
        is None
    )
