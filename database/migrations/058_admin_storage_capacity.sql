-- 058: capacidade global do Supabase Storage (Free), sem cotas individuais.
-- A instalacao e aditiva; main antiga continua funcionando ate o deploy novo.
-- Depois de aplicar na staging (projeto Supabase compartilhado), promover o
-- mesmo codigo para main; nao alterar storage.objects nem policies do Supabase.
CREATE TABLE IF NOT EXISTS public.storage_upload_reservations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 52428800),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 minutes')
);
ALTER TABLE public.storage_upload_reservations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.storage_upload_reservations FROM PUBLIC, anon, authenticated;
-- Sem acesso direto via PostgREST nem para service_role; somente as funcoes.

-- Retorna somente agregados; nomes e tamanhos de objetos nunca saem na resposta.
CREATE OR REPLACE FUNCTION public.admin_storage_snapshot()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_buckets jsonb;
    v_used bigint;
    v_reserved bigint;
BEGIN
    IF EXISTS (
        SELECT 1 FROM storage.objects AS o
        WHERE (o.metadata->>'size') IS NULL
           OR (o.metadata->>'size') !~ '^[0-9]{1,18}
        jsonb_build_object('bucket', x.bucket, 'objects', x.objects, 'used_bytes', x.used_bytes)
        ORDER BY x.bucket
    ), '[]'::jsonb), COALESCE(SUM(x.used_bytes), 0)::bigint
    INTO v_buckets, v_used
    FROM (
        SELECT o.bucket_id AS bucket, COUNT(*)::int AS objects,
               COALESCE(SUM(
                   CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
                        THEN (o.metadata->>'size')::bigint ELSE 0 END
               ), 0)::bigint AS used_bytes
        FROM storage.objects AS o
        GROUP BY o.bucket_id
    ) AS x;
    SELECT COALESCE(SUM(r.size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations AS r WHERE r.expires_at > now();
    RETURN jsonb_build_object(
        'used_bytes', v_used, 'reserved_bytes', v_reserved,
        'quota_bytes', 1073741824,
        'warning_percent', 75, 'critical_percent', 85, 'block_percent', 90,
        'buckets', v_buckets
    );
END;
$$;

-- Lock transacional serializa reservas entre staging e main, independentemente
-- de instancias do Render, sem Redis nem planos pagos.
CREATE OR REPLACE FUNCTION public.reserve_storage_upload(p_size_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_used bigint;
    v_reserved bigint;
    v_id uuid;
    v_quota bigint := 1073741824;
BEGIN
    IF p_size_bytes IS NULL OR p_size_bytes <= 0 OR p_size_bytes > 52428800 THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'invalid_size');
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(849501802);
    DELETE FROM public.storage_upload_reservations WHERE expires_at <= now();
    IF EXISTS (
        SELECT 1 FROM storage.objects AS o
        WHERE (o.metadata->>'size') IS NULL
           OR (o.metadata->>'size') !~ '^[0-9]{1,18}
        CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
             THEN (o.metadata->>'size')::bigint ELSE 0 END
    ), 0)::bigint INTO v_used FROM storage.objects AS o;
    SELECT COALESCE(SUM(size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations;
    IF v_used + v_reserved + p_size_bytes > (v_quota * 9 / 10) THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'capacity_reached');
    END IF;
    INSERT INTO public.storage_upload_reservations (size_bytes)
    VALUES (p_size_bytes) RETURNING id INTO v_id;
    RETURN jsonb_build_object('allowed', true, 'reservation_id', v_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.release_storage_upload(p_reservation_id uuid)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$
    DELETE FROM public.storage_upload_reservations WHERE id = p_reservation_id;
$$;

REVOKE ALL ON FUNCTION public.admin_storage_snapshot() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_storage_upload(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_storage_upload(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_storage_snapshot() TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_storage_upload(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_storage_upload(uuid) TO service_role;

    ) THEN
        RAISE EXCEPTION 'storage_metadata_invalid' USING ERRCODE = 'P0001';
    END IF;
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object('bucket', x.bucket, 'objects', x.objects, 'used_bytes', x.used_bytes)
        ORDER BY x.bucket
    ), '[]'::jsonb), COALESCE(SUM(x.used_bytes), 0)::bigint
    INTO v_buckets, v_used
    FROM (
        SELECT o.bucket_id AS bucket, COUNT(*)::int AS objects,
               COALESCE(SUM(
                   CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
                        THEN (o.metadata->>'size')::bigint ELSE 0 END
               ), 0)::bigint AS used_bytes
        FROM storage.objects AS o
        GROUP BY o.bucket_id
    ) AS x;
    SELECT COALESCE(SUM(r.size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations AS r WHERE r.expires_at > now();
    RETURN jsonb_build_object(
        'used_bytes', v_used, 'reserved_bytes', v_reserved,
        'quota_bytes', 1073741824,
        'warning_percent', 75, 'critical_percent', 85, 'block_percent', 90,
        'buckets', v_buckets
    );
END;
$$;

-- Lock transacional serializa reservas entre staging e main, independentemente
-- de instancias do Render, sem Redis nem planos pagos.
CREATE OR REPLACE FUNCTION public.reserve_storage_upload(p_size_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_used bigint;
    v_reserved bigint;
    v_id uuid;
    v_quota bigint := 1073741824;
BEGIN
    IF p_size_bytes IS NULL OR p_size_bytes <= 0 OR p_size_bytes > 52428800 THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'invalid_size');
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(849501802);
    DELETE FROM public.storage_upload_reservations WHERE expires_at <= now();
    SELECT COALESCE(SUM(
        CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
             THEN (o.metadata->>'size')::bigint ELSE 0 END
    ), 0)::bigint INTO v_used FROM storage.objects AS o;
    SELECT COALESCE(SUM(size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations;
    IF v_used + v_reserved + p_size_bytes > (v_quota * 9 / 10) THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'capacity_reached');
    END IF;
    INSERT INTO public.storage_upload_reservations (size_bytes)
    VALUES (p_size_bytes) RETURNING id INTO v_id;
    RETURN jsonb_build_object('allowed', true, 'reservation_id', v_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.release_storage_upload(p_reservation_id uuid)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$
    DELETE FROM public.storage_upload_reservations WHERE id = p_reservation_id;
$$;

REVOKE ALL ON FUNCTION public.admin_storage_snapshot() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_storage_upload(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_storage_upload(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_storage_snapshot() TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_storage_upload(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_storage_upload(uuid) TO service_role;

    ) THEN
        RAISE EXCEPTION 'storage_metadata_invalid' USING ERRCODE = 'P0001';
    END IF;
    SELECT COALESCE(SUM(
        CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
             THEN (o.metadata->>'size')::bigint ELSE 0 END
    ), 0)::bigint INTO v_used FROM storage.objects AS o;
    SELECT COALESCE(SUM(size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations;
    IF v_used + v_reserved + p_size_bytes > (v_quota * 9 / 10) THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'capacity_reached');
    END IF;
    INSERT INTO public.storage_upload_reservations (size_bytes)
    VALUES (p_size_bytes) RETURNING id INTO v_id;
    RETURN jsonb_build_object('allowed', true, 'reservation_id', v_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.release_storage_upload(p_reservation_id uuid)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$
    DELETE FROM public.storage_upload_reservations WHERE id = p_reservation_id;
$$;

REVOKE ALL ON FUNCTION public.admin_storage_snapshot() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_storage_upload(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_storage_upload(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_storage_snapshot() TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_storage_upload(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_storage_upload(uuid) TO service_role;

    ) THEN
        RAISE EXCEPTION 'storage_metadata_invalid' USING ERRCODE = 'P0001';
    END IF;
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object('bucket', x.bucket, 'objects', x.objects, 'used_bytes', x.used_bytes)
        ORDER BY x.bucket
    ), '[]'::jsonb), COALESCE(SUM(x.used_bytes), 0)::bigint
    INTO v_buckets, v_used
    FROM (
        SELECT o.bucket_id AS bucket, COUNT(*)::int AS objects,
               COALESCE(SUM(
                   CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
                        THEN (o.metadata->>'size')::bigint ELSE 0 END
               ), 0)::bigint AS used_bytes
        FROM storage.objects AS o
        GROUP BY o.bucket_id
    ) AS x;
    SELECT COALESCE(SUM(r.size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations AS r WHERE r.expires_at > now();
    RETURN jsonb_build_object(
        'used_bytes', v_used, 'reserved_bytes', v_reserved,
        'quota_bytes', 1073741824,
        'warning_percent', 75, 'critical_percent', 85, 'block_percent', 90,
        'buckets', v_buckets
    );
END;
$$;

-- Lock transacional serializa reservas entre staging e main, independentemente
-- de instancias do Render, sem Redis nem planos pagos.
CREATE OR REPLACE FUNCTION public.reserve_storage_upload(p_size_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_used bigint;
    v_reserved bigint;
    v_id uuid;
    v_quota bigint := 1073741824;
BEGIN
    IF p_size_bytes IS NULL OR p_size_bytes <= 0 OR p_size_bytes > 52428800 THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'invalid_size');
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(849501802);
    DELETE FROM public.storage_upload_reservations WHERE expires_at <= now();
    SELECT COALESCE(SUM(
        CASE WHEN (o.metadata->>'size') ~ '^[0-9]{1,18}$'
             THEN (o.metadata->>'size')::bigint ELSE 0 END
    ), 0)::bigint INTO v_used FROM storage.objects AS o;
    SELECT COALESCE(SUM(size_bytes), 0)::bigint INTO v_reserved
    FROM public.storage_upload_reservations;
    IF v_used + v_reserved + p_size_bytes > (v_quota * 9 / 10) THEN
        RETURN jsonb_build_object('allowed', false, 'reason', 'capacity_reached');
    END IF;
    INSERT INTO public.storage_upload_reservations (size_bytes)
    VALUES (p_size_bytes) RETURNING id INTO v_id;
    RETURN jsonb_build_object('allowed', true, 'reservation_id', v_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.release_storage_upload(p_reservation_id uuid)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$
    DELETE FROM public.storage_upload_reservations WHERE id = p_reservation_id;
$$;

REVOKE ALL ON FUNCTION public.admin_storage_snapshot() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_storage_upload(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_storage_upload(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_storage_snapshot() TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_storage_upload(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_storage_upload(uuid) TO service_role;
