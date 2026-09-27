"""API routers package."""

from .auth import router as auth_router
from .products import router as products_router
from .lists import router as lists_router
from .posts import router as posts_router
from .credentials import router as credentials_router
from .users import router as users_router
from .dashboard import router as dashboard_router
from .notifications import router as notifications_router

__all__ = [
    "auth_router",
    "products_router",
    "lists_router",
    "posts_router",
    "credentials_router",
    "users_router",
    "dashboard_router",
    "notifications_router",
]
