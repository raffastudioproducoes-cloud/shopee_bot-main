"""
Settings para a API Python do Auto Orbital.
Carrega variáveis de ambiente via pydantic-settings.
"""

import os

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# HS256 com segredo curto/vazio deixa qualquer um forjar o JWT de sessão.
MIN_API_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    # Supabase Auth (somente publicável no servidor; nunca usar service_role no fluxo de login).
    supabase_auth_enabled: bool = False
    # Cadastro email exige confirmação real pelo Supabase Auth.
    supabase_auth_email_signup_enabled: bool = True
    supabase_auth_publishable_key: str = ""
    supabase_auth_redirect_base_url: str = ""
    # Exceção temporária para um único usuário legado de testes da Shopee.
    # Vazio por padrão: nunca habilitar login antigo indiscriminadamente.
    supabase_legacy_support_username: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    api_secret_key: str = ""
    frontend_url: str = "http://localhost:5173"
    # Histórico de requisições (api/middleware.py) — desligado por padrão pra
    # não gravar nada nos testes nem em quem roda a API localmente sem querer
    # auditoria; produção liga via env var REQUEST_LOGGING_ENABLED=true.
    request_logging_enabled: bool = False
    # Cobrança Asaas. Sem chave a cobrança fica desligada (rotas respondem 503).
    # Staging usa o sandbox; produção, a conta real (chaves diferentes).
    asaas_api_key: str = ""
    asaas_api_url: str = "https://api-sandbox.asaas.com/v3"
    asaas_webhook_token: str = ""
    asaas_user_agent: str = "AutoOrbital/1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @field_validator("cors_origins")
    @classmethod
    def _explicit_cors_origins(cls, origins: list[str]) -> list[str]:
        """CORS com credenciais so aceita origem explicita: descarta '*' e
        'null' e normaliza barra final (prod/staging/localhost via CORS_ORIGINS)."""
        cleaned = [o.strip().rstrip("/") for o in origins]
        return [o for o in dict.fromkeys(cleaned) if o and o not in ("*", "null")]


def validate_secrets(cfg) -> None:
    """Aborta o startup se faltar segredo obrigatório. Mensagens nunca
    incluem o valor (vão parar no log do Render)."""
    if len(cfg.api_secret_key or "") < MIN_API_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"API_SECRET_KEY ausente ou curta (mínimo {MIN_API_SECRET_KEY_LENGTH} "
            "caracteres). Defina a variável de ambiente antes de subir a API."
        )
    # Mesma leitura de api/crypto.py (os.environ, não o .env do pydantic).
    try:
        Fernet(os.environ.get("APP_ENCRYPTION_KEY", "").encode("ascii"))
    except ValueError:  # inclui binascii.Error e UnicodeEncodeError
        raise RuntimeError(
            "APP_ENCRYPTION_KEY ausente ou inválida (precisa ser uma chave "
            "Fernet: 32 bytes em base64 url-safe). Defina a variável de ambiente."
        ) from None


settings = Settings()
validate_secrets(settings)
