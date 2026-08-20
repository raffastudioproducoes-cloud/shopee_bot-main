CREATE TABLE IF NOT EXISTS schedulers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    func TEXT NOT NULL,
    trigger TEXT NOT NULL,
    time TIME,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
    start_date TIMESTAMP,
    run_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
