CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    original_link TEXT NOT NULL,
    commission_link TEXT NOT NULL,
    commission TEXT,
    image TEXT,
    price_min TEXT,
    price_max TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    user_id UUID NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (product_id, user_id)
);
