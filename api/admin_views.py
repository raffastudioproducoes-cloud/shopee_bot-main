"""Projeções ADMIN sem identidades ou diagnósticos em texto livre."""
from datetime import datetime, timezone
from typing import Literal
from fastapi.routing import APIRoute
from pydantic import BaseModel, field_validator, computed_field


class AdminLogEntry(BaseModel):
    method: str
    path: str
    status_code: int | None = None
    duration_ms: int | None = None
    created_at: datetime

    @field_validator('path')
    @classmethod
    def route_template(cls, value: str) -> str:
        # Só templates registrados: nunca repassar parâmetros, queries ou rotas desconhecidas.
        from .main import app
        if not value.startswith('/'):
            return 'Rota não identificada'
        path = value.partition('?')[0].partition('#')[0]
        if path.startswith('/api/'):
            path = path[4:]
        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue
            pattern = getattr(route, 'path_regex', None)
            if pattern and pattern.fullmatch(path):
                return route.path
        return 'Rota não identificada'

    @field_validator('method')
    @classmethod
    def known_method(cls, value: str) -> str:
        return value if value in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'} else 'OUTRO'

    @field_validator('created_at')
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AdminLogsResponse(BaseModel):
    data: list[AdminLogEntry]
    total: int
    limit: int
    offset: int


class AdminCredentialStatus(BaseModel):
    connected: bool
    light: Literal['green', 'yellow', 'red']
    state: Literal['disconnected', 'untested', 'expired', 'error', 'stale', 'ok', 'testing']
    checked_at: datetime | None = None

    @computed_field
    @property
    def status_text(self) -> str:
        return {
            'disconnected': 'Desconectado', 'untested': 'Salva, ainda não testada',
            'expired': 'Conexão expirada', 'error': 'Falha no teste de conexão',
            'stale': 'Teste antigo; verifique a conexão', 'ok': 'Funcionando', 'testing': 'Testando…',
        }[self.state]
