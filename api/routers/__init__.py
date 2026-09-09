"""API routers package."""

from .auth import router as auth_router
from .products import router as products_router
from .lists import router as lists_router

__all__ = ["auth_router", "products_router", "lists_router"]
