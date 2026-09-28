-- Histórico de toda requisição à API nova (api/middleware.py). Existe pra
-- debug remoto: ao invés de pedir print/log de cada erro de produção, dá pra
-- consultar essa tabela direto. `user_id`/`username` são melhor esforço (só
-- preenchidos quando o cookie access_token existe e decodifica); sem FK pra
-- users porque o log deve sobreviver mesmo se a conta for apagada depois.
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    username TEXT,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    error TEXT,
    redirect_to TEXT,
    client_ip TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_request_logs_status_code ON request_logs (status_code);
