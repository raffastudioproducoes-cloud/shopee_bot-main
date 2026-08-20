CREATE TABLE IF NOT EXISTS product_lists_products (
    product_list_id INTEGER REFERENCES product_lists(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    PRIMARY KEY (product_list_id, product_id)
);
