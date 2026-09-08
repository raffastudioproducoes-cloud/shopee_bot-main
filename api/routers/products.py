"""
Router placeholder — Products (API Python)
CRUD de produtos da Shopee.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    shopee_link: str | None = None


@router.get("/")
async def list_products():
    raise HTTPException(status_code=501, detail="Endpoint não implementado")


@router.post("/")
async def create_product():
    raise HTTPException(status_code=501, detail="Endpoint não implementado")
