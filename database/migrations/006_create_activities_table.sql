CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    metadata JSONB DEFAULT '{}'::JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    activity_id INTEGER NOT NULL,
    user_id UUID NOT NULL,
    FOREIGN KEY (activity_id) REFERENCES activity_types(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
