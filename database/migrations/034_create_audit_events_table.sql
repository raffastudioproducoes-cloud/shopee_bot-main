-- Auditoria imutável de alterações sensíveis (preço, exclusão, dado sensível).
-- Diferente de `activities` (eventos de post/bot): aqui é rastro de MUDANÇA
-- de dado, quem fez, quando e o que era antes/depois.
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    -- SET NULL (não CASCADE nem sem FK): sobrevive à exclusão da conta —
    -- igual ao espírito de `request_logs` (migração 029) — mas sem
    -- abrir mão da FK, então o rastro fica órfão (user_id NULL) em vez
    -- de travar a exclusão (era o bug: sem regra ON DELETE, Postgres
    -- rejeitava excluir qualquer usuário com linha de auditoria).
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events (entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events (user_id);

ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "block_all_api" ON audit_events FOR ALL USING (false) WITH CHECK (false);
