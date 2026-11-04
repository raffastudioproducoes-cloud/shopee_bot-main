-- 085: proteção compatível com produção antiga contra DELETE físico.
-- O Supabase é compartilhado entre main e staging. A API antiga em main
-- ainda chama DELETE direto; sem este gate apagaria históricos por CASCADE.
-- Nenhum cron, job, fila ou dado existente é modificado.
BEGIN;
SET LOCAL lock_timeout='5s';

CREATE OR REPLACE FUNCTION public.guard_history_against_legacy_delete()
RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
DECLARE
  v_authorized_user text;
BEGIN
  IF TG_TABLE_SCHEMA <> 'public' THEN
    RAISE EXCEPTION 'legacy_delete_blocked' USING ERRCODE='P0001';
  END IF;

  IF TG_TABLE_NAME='users' THEN
    -- Apenas a tarefa de apagamento integral com Storage + Auth já
    -- confirmados pode remover a conta e iniciar suas cascatas.
    PERFORM 1 FROM public.account_erasure_tasks
      WHERE user_id=OLD.id
        AND storage_complete_at IS NOT NULL
        AND auth_complete_at IS NOT NULL
      FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'use_account_erasure_flow' USING ERRCODE='P0001';
    END IF;
    -- Escopo *transacional*, apenas para cascatas desse mesmo titular.
    PERFORM set_config('app.account_erasure_authorized_user', OLD.id::text, true);
    RETURN OLD;
  END IF;

  IF TG_TABLE_NAME='profiles' THEN
    v_authorized_user := current_setting(
      'app.account_erasure_authorized_user', true);
    IF v_authorized_user IS DISTINCT FROM OLD.user_id::text
       OR NOT EXISTS (
         SELECT 1 FROM public.account_erasure_tasks
         WHERE user_id=OLD.user_id
           AND storage_complete_at IS NOT NULL
           AND auth_complete_at IS NOT NULL
       ) THEN
      RAISE EXCEPTION 'use_profile_archive_with_history'
        USING ERRCODE='P0001';
    END IF;
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'unsupported_guard_table' USING ERRCODE='P0001';
END; $fn$;

DO $do$
BEGIN
  IF NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgrelid='public.users'::regclass
        AND tgname='trg_guard_user_erasure_flow' AND NOT tgisinternal
  ) THEN
    CREATE TRIGGER trg_guard_user_erasure_flow
      BEFORE DELETE ON public.users
      FOR EACH ROW EXECUTE FUNCTION public.guard_history_against_legacy_delete();
  END IF;
  IF NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgrelid='public.profiles'::regclass
        AND tgname='trg_guard_profile_history' AND NOT tgisinternal
  ) THEN
    CREATE TRIGGER trg_guard_profile_history
      BEFORE DELETE ON public.profiles
      FOR EACH ROW EXECUTE FUNCTION public.guard_history_against_legacy_delete();
  END IF;
END; $do$;

REVOKE ALL ON FUNCTION public.guard_history_against_legacy_delete()
  FROM PUBLIC,anon,authenticated;
COMMIT;
