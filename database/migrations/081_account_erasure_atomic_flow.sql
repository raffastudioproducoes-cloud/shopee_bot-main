-- 081 - apagamento integral da conta em passos idempotentes.
-- Não desativa nem modifica pg_cron, pg_net, scheduler ou serviços.
-- Requer backend autorizado e Storage/Auth Admin API antes da finalização.
BEGIN;
SET LOCAL lock_timeout='5s';

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS account_deletion_started_at timestamptz;

CREATE TABLE IF NOT EXISTS public.account_erasure_tasks (
  user_id uuid PRIMARY KEY,
  auth_user_id uuid,
  started_at timestamptz NOT NULL DEFAULT now(),
  storage_complete_at timestamptz,
  auth_complete_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.account_erasure_tasks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.account_erasure_tasks FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE public.account_erasure_tasks TO service_role;

CREATE OR REPLACE FUNCTION public.begin_account_erasure(p_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
DECLARE
  v_user record; v_res record; v_now timestamptz:=now();
BEGIN
  SELECT id,username,supabase_auth_user_id,account_deletion_started_at
    INTO v_user FROM public.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'account_not_found' USING ERRCODE='P0001'; END IF;
  IF lower(v_user.username)='rafastudio' THEN
    RAISE EXCEPTION 'protected_account' USING ERRCODE='P0001';
  END IF;
  INSERT INTO public.account_erasure_tasks(user_id,auth_user_id)
    VALUES (p_user_id,v_user.supabase_auth_user_id)
    ON CONFLICT (user_id) DO NOTHING;
  UPDATE public.users SET
    account_deletion_started_at=coalesce(account_deletion_started_at,v_now)
    WHERE id=p_user_id;
  UPDATE public.schedulers SET
    dispatch_cancelled_at=coalesce(dispatch_cancelled_at,v_now),
    dispatch_revision=dispatch_revision+1
    WHERE user_id=p_user_id AND dispatch_cancelled_at IS NULL;
  FOR v_res IN SELECT id,profile_id FROM public.campaign_reservations_f4e
    WHERE user_id=p_user_id AND lifecycle IN ('preparing','active','paused')
    ORDER BY id
  LOOP
    PERFORM public.change_campaign_lifecycle_f4e(
      p_user_id,v_res.profile_id,v_res.id,'cancel');
  END LOOP;
  RETURN jsonb_build_object('user_id',p_user_id,
       'auth_user_id',v_user.supabase_auth_user_id);
END; $fn$;

-- Seleciona por dono Auth OU por referências verificadas no banco. Não varre
-- outros usuários nem remove objetos diretamente por SQL.
CREATE OR REPLACE FUNCTION public.account_erasure_storage_manifest(
    p_user_id uuid, p_limit integer DEFAULT 100)
RETURNS TABLE(bucket_id text, object_name text)
LANGUAGE sql SECURITY INVOKER SET search_path TO '' AS $fn$
  SELECT o.bucket_id,o.name
  FROM storage.objects o
  JOIN public.account_erasure_tasks t ON t.user_id=p_user_id
  WHERE o.bucket_id IN ('post-media','avatars')
    AND (
      (t.auth_user_id IS NOT NULL AND (
        o.owner=t.auth_user_id OR o.owner_id=t.auth_user_id::text))
      OR (
        o.bucket_id='avatars' AND EXISTS (
          SELECT 1 FROM public.profiles p
          WHERE p.user_id=p_user_id AND split_part(o.name,'/',1)=p.id::text))
      OR (
        o.bucket_id='post-media' AND (
          split_part(o.name,'/',1)=p_user_id::text
          OR split_part(o.name,'/',2)=p_user_id::text
          OR EXISTS (SELECT 1 FROM public.medias m
            WHERE m.user_id=p_user_id
              AND m.file_path='storage://'||o.bucket_id||'/'||o.name)
          OR EXISTS (SELECT 1 FROM public.temporary_media_uploads tm
            WHERE tm.user_id=p_user_id
              AND tm.storage_bucket=o.bucket_id AND tm.storage_key=o.name)
          OR EXISTS (SELECT 1 FROM public.campaign_draft_media dm
            WHERE dm.user_id=p_user_id
              AND dm.storage_bucket=o.bucket_id AND dm.storage_key=o.name)
          OR EXISTS (SELECT 1 FROM public.campaign_reservation_assets_f4e a
            WHERE a.user_id=p_user_id AND a.storage_key=o.name)
        ))
    )
  ORDER BY o.bucket_id,o.name
  LIMIT greatest(1,least(coalesce(p_limit,100),500));
$fn$;

CREATE OR REPLACE FUNCTION public.mark_account_erasure_storage_complete(p_user_id uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
BEGIN
  PERFORM 1 FROM public.account_erasure_tasks WHERE user_id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'erasure_task_missing' USING ERRCODE='P0001'; END IF;
  IF EXISTS (SELECT 1 FROM public.account_erasure_storage_manifest(p_user_id,1)) THEN
    RAISE EXCEPTION 'storage_objects_remaining' USING ERRCODE='P0001';
  END IF;
  UPDATE public.account_erasure_tasks SET storage_complete_at=now(),updated_at=now()
    WHERE user_id=p_user_id;
  RETURN true;
END; $fn$;

CREATE OR REPLACE FUNCTION public.mark_account_erasure_auth_complete(p_user_id uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
BEGIN
  UPDATE public.account_erasure_tasks SET auth_complete_at=now(),updated_at=now()
    WHERE user_id=p_user_id AND storage_complete_at IS NOT NULL;
  IF NOT FOUND THEN RAISE EXCEPTION 'storage_not_complete' USING ERRCODE='P0001'; END IF;
  RETURN true;
END; $fn$;

CREATE OR REPLACE FUNCTION public.finalize_account_erasure(p_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $fn$
DECLARE
  v_task record; v_tbl record; v_deleted integer;
BEGIN
  PERFORM 1 FROM public.users WHERE id=p_user_id FOR UPDATE;
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
    OR profile_id IN (SELECT id FROM public.profiles WHERE user_id=p_user_id);
  DELETE FROM public.campaign_progress_f4e WHERE user_id=p_user_id;
  DELETE FROM public.post_content_revisions WHERE user_id=p_user_id;
  DELETE FROM public.users WHERE id=p_user_id;
  GET DIAGNOSTICS v_deleted=ROW_COUNT;
  IF v_deleted<>1 THEN RAISE EXCEPTION 'account_not_deleted' USING ERRCODE='P0001'; END IF;
  DELETE FROM public.account_erasure_tasks WHERE user_id=p_user_id;
  RETURN jsonb_build_object('status','deleted');
END; $fn$;

REVOKE ALL ON FUNCTION public.begin_account_erasure(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.account_erasure_storage_manifest(uuid,integer) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.mark_account_erasure_storage_complete(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.mark_account_erasure_auth_complete(uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.finalize_account_erasure(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.begin_account_erasure(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.account_erasure_storage_manifest(uuid,integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.mark_account_erasure_storage_complete(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.mark_account_erasure_auth_complete(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.finalize_account_erasure(uuid) TO service_role;
COMMIT;
