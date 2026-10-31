"""Ambiente isolado para testes Flask, sem conexão com banco remoto."""

import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[2]
os.environ.setdefault("FLASK_MAX_CONTENT_LENGTH", "52428800")
os.environ.setdefault("FLASK_SESSION_SECRET", "test_only_secret")
os.environ.setdefault("FLASK_UPLOAD_FOLDER", tempfile.gettempdir())
os.environ.setdefault("FLASK_DEBUG", "false")

if "shopee_bot" not in sys.modules:
    package = types.ModuleType("shopee_bot")
    package.__path__ = [str(project_root)]
    sys.modules["shopee_bot"] = package


@pytest.fixture
def client():
    from shopee_bot.web import app

    with app.test_client() as flask_client:
        yield flask_client
