"""Credentials Router — API Python (FastAPI)

Endpoints para gerenciamento de credenciais cifradas de redes sociais.
Coexists with Flask during migration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialSave(BaseModel):
    app_id: str | None = None
    secret: str | None = None
    access_token: str | None = None


@router.get("/")
async def list_credentials():
    raise HTTPException(status_code=501, detail="Endpoint não implementado")


@router.get("/{network}/{user_id}")
async def get_credential(network: str, user_id: str):
    raise HTTPException(status_code=501, detail="Endpoint não implementado")


@router.put("/{network}/{user_id}")
async def save_credential(network: str, user_id: str, data: CredentialSave):
    raise HTTPException(status_code=501, detail="Endpoint não implementado")


@router.delete("/{network}/{user_id}")
async def delete_credential(network: str, user_id: str):
    raise HTTPException(status_code=501, detail="Endpoint não implementado")
