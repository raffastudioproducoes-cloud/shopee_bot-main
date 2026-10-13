-- Recorrência por vários dias sem invalidar jobs existentes que usam apenas
-- day_of_week. A lista é validada no banco e na API antes de chegar ao cron.
BEGIN;

ALTER TABLE public.schedulers
    ADD COLUMN IF NOT EXISTS days_of_week SMALLINT[];

ALTER TABLE public.schedulers
    DROP CONSTRAINT IF EXISTS schedulers_days_of_week_check;

ALTER TABLE public.schedulers
    ADD CONSTRAINT schedulers_days_of_week_check
    CHECK (
        days_of_week IS NULL
        OR (
            cardinality(days_of_week) BETWEEN 1 AND 7
            AND days_of_week <@ ARRAY[0, 1, 2, 3, 4, 5, 6]::SMALLINT[]
        )
    );

UPDATE public.schedulers
SET days_of_week = ARRAY[day_of_week]::SMALLINT[]
WHERE trigger = 'cron'
  AND days_of_week IS NULL
  AND day_of_week IS NOT NULL;

COMMIT;
