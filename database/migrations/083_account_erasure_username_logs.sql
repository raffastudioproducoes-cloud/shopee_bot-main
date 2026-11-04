-- 083: expurgo de logs que só guardam username (sem user_id).
BEGIN;
SET LOCAL lock_timeout='5s';
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
  DELETE FROM public.users WHERE id=p_user_id;
  GET DIAGNOSTICS v_deleted=ROW_COUNT;
  IF v_deleted<>1 THEN RAISE EXCEPTION 'account_not_deleted' USING ERRCODE='P0001'; END IF;
  DELETE FROM public.account_erasure_tasks WHERE user_id=p_user_id;
  RETURN jsonb_build_object('status','deleted');
END; $fn$;

COMMIT;
