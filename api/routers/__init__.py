from fastapi import APIRouter

router = APIRouter()

# Import dos routers para registrar no app
from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .posts import router as posts_router
from .credentials import router as credentials_router
