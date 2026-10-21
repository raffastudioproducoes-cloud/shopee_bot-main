ALTER TABLE public.posts
    ADD COLUMN IF NOT EXISTS publish_immediately boolean NOT NULL DEFAULT false;
