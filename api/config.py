"""
Settings para a API Python do Shopee Auto Vendas.
Carrega variáveis de ambiente via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    api_secret_key: str = ""
    frontend_url: str = "http://localhost:5173"
    # Histórico de requisições (api/middleware.py) — desligado por padrão pra
    # não gravar nada nos testes nem em quem roda a API localmente sem querer
    # auditoria; produção liga via env var REQUEST_LOGGING_ENABLED=true.
    request_logging_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
