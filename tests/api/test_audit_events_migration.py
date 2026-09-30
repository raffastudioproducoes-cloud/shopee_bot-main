"""Regressão do item 1 (HIGH) da revisão de segurança: a FK
`audit_events.user_id -> users(id)` precisa de `ON DELETE SET NULL` (ou
não ter FK, como `request_logs`) — sem isso, excluir QUALQUER usuário que
já tenha gerado uma linha de auditoria (preço mudado, produto deletado,
autoexclusão) violava a constraint e o Postgres rejeitava o DELETE.

Não há suite de integração com Postgres real neste projeto (Supabase é
sempre mockado nos testes), então a checagem possível e barata aqui é
sobre o arquivo de migração em si — garante que ninguém reintroduz a FK
sem regra `ON DELETE` por engano numa edição futura."""

from pathlib import Path

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "database" / "migrations"
    / "034_create_audit_events_table.sql"
)


def test_audit_events_user_id_fk_has_on_delete_set_null():
    sql = _MIGRATION_PATH.read_text(encoding="utf-8")

    assert "REFERENCES users(id) ON DELETE SET NULL" in sql, (
        "audit_events.user_id precisa de ON DELETE SET NULL — sem isso, "
        "excluir um usuário com histórico de auditoria quebra com "
        "violação de FK (ver item 1 da revisão de segurança)."
    )
    assert "ON DELETE CASCADE" not in sql, (
        "audit_events.user_id NÃO pode ser ON DELETE CASCADE — apagaria "
        "a própria trilha de auditoria que a tabela existe pra preservar."
    )
