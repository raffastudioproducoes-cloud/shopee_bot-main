"""
Settings para a API Python do Shopee Auto Vendas.
Carrega variáveis de ambiente via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    api_secret_key: str = ""

    model_config = {"extra": "allow"}


settings = Settings()
