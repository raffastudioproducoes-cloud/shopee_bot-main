CREATE TABLE IF NOT EXISTS posts_products (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    display_order INTEGER NOT NULL,
    PRIMARY KEY (post_id, product_id)
);
