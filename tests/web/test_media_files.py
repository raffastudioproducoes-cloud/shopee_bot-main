"""Remoção local de mídia no Flask: caminho `storage://` não é arquivo."""

import importlib.util
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[2] / "web" / "media_files.py"


def _load():
    spec = importlib.util.spec_from_file_location("_test_media_files", _PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_storage_path_is_ignored_without_touching_filesystem(monkeypatch):
    module = _load()
    calls = []
    monkeypatch.setattr(module.os, "remove", lambda path: calls.append(path))

    module.remove_local_media("storage://post-media/drafts/42/p/a.jpg")

    assert calls == []


def test_local_path_is_removed(tmp_path):
    module = _load()
    target = tmp_path / "a.jpg"
    target.write_bytes(b"x")

    module.remove_local_media(str(target))

    assert not target.exists()


def test_missing_local_file_does_not_raise(tmp_path):
    _load().remove_local_media(str(tmp_path / "sumiu.jpg"))
