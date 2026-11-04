-- 086: o último DELETE da conta só pode acontecer dentro da RPC finalizadora.
-- Impede o main legado de pular a limpeza de audit/request_logs no intervalo
-- entre a confirmação de Storage/Auth e a remoção transacional da conta.
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
    IF current_setting('app.account_erasure_finalize_user',true)
       IS DISTINCT FROM OLD.id::text THEN
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

CREATE OR REPLACE FUNCTION public.finalize_account_erasure(p_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
DECLARE
  v_task record; v_tbl record; v_deleted integer; v_username text;
BEGIN
  SELECT username INTO v_username FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  SELECT storage_complete_at,auth_complete_at INTO v_task
    FROM public.account_erasure_tasks WHERE user_id=p_user_id FOR UPDATE;
  IF NOT FOUND OR v_task.storage_complete_at IS NULL OR v_task.auth_complete_at IS NULL THEN
    RAISE EXCEPTION 'erasure_steps_incomplete' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM public.account_erasure_storage_manifest(p_user_id,1)) THEN
    RAISE EXCEPTION 'storage_objects_remaining' USING ERRCODE='P0001';
  END IF;

  -- Limpar primeiro eventos sem FK CASCADE; audit_events.user_id usa SET NULL,
  -- request_logs não tem FK e campaign_progress_f4e também é independente.
  DELETE FROM public.audit_events
   WHERE user_id=p_user_id
     OR entity_id=p_user_id::text
     OR profile_id IN (SELECT id FROM public.profiles WHERE user_id=p_user_id)
     OR coalesce(old_value::text,'') LIKE '%'||p_user_id::text||'%'
     OR coalesce(new_value::text,'') LIKE '%'||p_user_id::text||'%';

  -- Identificar também auditoria de recursos desta conta registrada por admin
  -- (audit_events.user_id pode ser o administrador, não o dono do recurso).
  FOR v_tbl IN
    SELECT c.table_name FROM information_schema.columns c
    JOIN information_schema.columns idc
      ON idc.table_schema=c.table_schema
     AND idc.table_name=c.table_name AND idc.column_name='id'
    WHERE c.table_schema='public' AND c.column_name='user_id'
      AND c.table_name NOT IN ('audit_events','account_erasure_tasks')
  LOOP
    EXECUTE format('DELETE FROM public.audit_events a WHERE a.entity_id IN
      (SELECT id::text FROM public.%I WHERE user_id=$1)',v_tbl.table_name)
      USING p_user_id;
  END LOOP;

  DELETE FROM public.request_logs WHERE user_id=p_user_id
    OR (v_username IS NOT NULL AND lower(username)=lower(v_username))
    OR profile_id IN (SELECT id FROM public.profiles WHERE user_id=p_user_id);
  -- campaign_progress_f4e é VIEW agregada, não tabela: dados vêm das origens CASCADE.
  DELETE FROM public.post_content_revisions WHERE user_id=p_user_id;
  -- Só a RPC finalizadora habilita o DELETE; chamada direta legada bloqueada.
  PERFORM set_config('app.account_erasure_finalize_user',p_user_id::text,true);
  DELETE FROM public.users WHERE id=p_user_id;
  GET DIAGNOSTICS v_deleted=ROW_COUNT;
  IF v_deleted<>1 THEN RAISE EXCEPTION 'account_not_deleted' USING ERRCODE='P0001'; END IF;
  PERFORM set_config('app.account_erasure_finalize_user','',true);
  DELETE FROM public.account_erasure_tasks WHERE user_id=p_user_id;
  RETURN jsonb_build_object('status','deleted');
END; $fn$;

COMMIT;
