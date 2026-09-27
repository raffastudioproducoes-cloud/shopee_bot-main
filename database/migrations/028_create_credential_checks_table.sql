-- Guarda o resultado do último "Testar conexão" (POST /credentials/{network}/test)
-- por usuário+rede. Separado das tabelas *_credentials porque `status` nelas já
-- significa "tem credencial salva" — este é um conceito diferente ("a última vez
-- que alguém testou, funcionou?"), lido por TODOS os usuários (luz do sinalizador)
-- mas só escrito por ADMIN (botão "Testar conexão" é admin-only).
CREATE TABLE IF NOT EXISTS credential_checks (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    network TEXT NOT NULL,
    state TEXT NOT NULL, -- 'ok' (verde) | 'error' (amarelo)
    message TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, network)
);
