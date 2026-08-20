-- loga atividades do bot e scheduler (inicialmente)
CREATE TABLE IF NOT EXISTS activity_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO activity_types (id, name, description) VALUES
    (1, 'bot_post_success', 'Postagem realizada.'),
    (2, 'bot_post_failure', 'Houve um erro na postagem.'),
    (3, 'bot_reset_success', 'Dados do bot resetados.'),
    (4, 'bot_reset_failure', 'Houve um erro ao apagar os dados do bot.'),
    (5, 'bot_login_success', 'Bot logado.'),
    (6, 'bot_login_failure', 'Houve um erro ao logar com o bot.'),

    (7, 'scheduler_start', 'Agendador iniciou a tarefa.'),
    (8, 'scheduler_success', 'Agendador concluiu a tarefa.'),
    (9, 'scheduler_failure', 'Houve um erro durante a tarefa.'),
    (10, 'scheduler_info', 'Agendador informa.')
ON CONFLICT (id) DO NOTHING;
