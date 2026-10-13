"""A versão da Graph API fica numa única constante compartilhada."""
import re
from pathlib import Path

from apis import meta_version
from api import facebook_oauth, instagram_oauth

ROOT = Path(__file__).resolve().parents[2]
META_FILES = ("api/facebook_oauth.py", "api/instagram_oauth.py", "apis/facebook.py", "apis/instagram.py")


def test_graph_version_is_v26():
    assert meta_version.GRAPH_VERSION == "v26.0"
    assert meta_version.GRAPH_BASE == "https://graph.facebook.com/v26.0"


def test_oauth_modules_use_shared_version():
    assert facebook_oauth.API_VERSION == meta_version.GRAPH_VERSION
    assert instagram_oauth.API_VERSION == meta_version.GRAPH_VERSION


def test_no_meta_file_hardcodes_a_graph_version():
    for rel in META_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        assert not re.search(r'v\d{2}\.0["/]', code), rel
