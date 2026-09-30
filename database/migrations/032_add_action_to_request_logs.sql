-- Reusa request_logs (já tem user_id/username/created_at/error, ver 029)
-- pra também guardar passo de negócio explícito (ex: "iniciou OAuth do
-- Instagram", "token trocado", "post publicado") em vez de criar uma
-- tabela paralela. `action` é NULL nas linhas de requisição HTTP
-- normais (gravadas pelo middleware, api/middleware.py) e preenchido só
-- nas linhas de passo de negócio (gravadas por api/audit_log.py::log_action) —
-- filtro simples: `WHERE action IS NOT NULL` isola o log de negócio do
-- log de requisição.
ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS action TEXT;

CREATE INDEX IF NOT EXISTS idx_request_logs_action ON request_logs (action) WHERE action IS NOT NULL;
