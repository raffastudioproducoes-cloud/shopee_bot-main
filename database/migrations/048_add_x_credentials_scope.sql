-- Escopo OAuth concedido pelo X (texto separado por espaço, como no token).
-- NULL = conexão antiga/desconhecida: a API trata como sem media.write até
-- reconectar ou um refresh devolver o escopo real. Aditiva e idempotente.
ALTER TABLE x_credentials
    ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT NULL;
