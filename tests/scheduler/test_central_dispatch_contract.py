"""Contrato de autoridade de publicação com Supabase compartilhado.

Um site staging só de desenvolvimento não é um segundo executor externo.
Estes testes não acessam Supabase, Render ou redes sociais.
"""
import pytest

from shopee_bot.database.scheduler_environment import (
    current_environment,
    publication_executor_environment,
)


@pytest.mark.parametrize("site", ["main", "staging"])
def test_both_sites_target_same_central_publication_executor(monkeypatch, site):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_GIT_BRANCH", site)
    assert publication_executor_environment() == "production"


def test_central_execution_does_not_erase_runtime_identity(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "staging")
    assert current_environment() == "staging"
    assert publication_executor_environment() == "production"


def test_unknown_render_branch_still_fails_closed(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "preview-branch")
    with pytest.raises(RuntimeError, match="somente main e staging"):
        publication_executor_environment()
