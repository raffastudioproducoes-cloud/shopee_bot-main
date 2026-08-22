CREATE TABLE IF NOT EXISTS posts_medias (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    media_id INTEGER REFERENCES medias(id) ON DELETE CASCADE,
    display_order INTEGER NOT NULL,
    PRIMARY KEY (post_id, media_id)
);

CREATE OR REPLACE FUNCTION cleanup_orphan_medias()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM medias m
    WHERE NOT EXISTS (
        SELECT 1 FROM posts_medias pm WHERE pm.media_id = m.id
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

CREATE TRIGGER cleanup_medias
AFTER DELETE ON posts_medias
FOR EACH STATEMENT
EXECUTE FUNCTION cleanup_orphan_medias();
