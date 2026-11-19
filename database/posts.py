import sys

import pytz
from datetime import datetime
from shopee_bot.database import query_db, execute_db
from shopee_bot.database import post_content_snapshot, post_link_redirects
from api.network_text import unwrap_network_text


def count(user_id):
    query = "SELECT COUNT(*) FROM posts WHERE user_id = %s AND post_id IS NULL"
    return query_db(query, (user_id, ), True)["count"]


def get_tiktok_options(user_id, post_id, profile_id):
    """Escolhas do TikTok confirmadas pelo usuário para a head do post.

    Post de campanha: o item do snapshot congelado da reserva (mesmo produto do
    slot), já que a materialização não copia o JSON para a linha do post.
    None = não há consentimento registrado (o publicador recusa)."""
    query = """
        SELECT COALESCE(p.tiktok_options, (
            SELECT i->'tiktok'
            FROM public.campaign_network_slots_f4e s
            JOIN public.campaign_reservations_f4e r ON r.id = s.reservation_id
            CROSS JOIN LATERAL jsonb_array_elements(r.draft_snapshot->'items') i
            WHERE s.post_id = p.id AND s.network = 'tiktok'
              AND (i->>'product_id')::integer = s.product_id
              AND jsonb_typeof(i->'tiktok') = 'object'
            LIMIT 1
        )) AS options
        FROM public.posts p
        WHERE p.id = %s AND p.user_id = %s AND p.profile_id = %s::uuid
          AND p.post_id IS NULL
    """
    row = query_db(query, (post_id, user_id, profile_id), True)
    return row["options"] if row else None


# Escolha "Publicar como Reels" do Facebook, sem coluna nova: na head do post fica em
# posts.tiktok_options (jsonb anulável da migração 104, que só a head do TikTok usava)
# como {"reels": bool}; em campanha, no item do snapshot (`facebook_reels`). Ausente =
# comportamento antigo (vídeo comum).
FACEBOOK_REELS_SQL = """COALESCE(
    CASE WHEN p.network = 'facebook' AND jsonb_typeof(p.tiktok_options->'reels') = 'boolean'
         THEN (p.tiktok_options->>'reels')::boolean END,
    (
        SELECT (i->>'facebook_reels')::boolean
        FROM public.campaign_network_slots_f4e s
        JOIN public.campaign_reservations_f4e r ON r.id = s.reservation_id
        CROSS JOIN LATERAL jsonb_array_elements(r.draft_snapshot->'items') i
        WHERE s.post_id = p.id AND s.network = 'facebook'
          AND (i->>'product_id')::integer = s.product_id
          AND jsonb_typeof(i->'facebook_reels') = 'boolean'
        LIMIT 1
    ),
    false)"""


def get_facebook_reels(user_id, post_id, profile_id):
    """True quando o usuário escolheu publicar o vídeo do Facebook como Reels."""
    query = f"""
        SELECT {FACEBOOK_REELS_SQL} AS reels
        FROM public.posts p
        WHERE p.id = %s AND p.user_id = %s AND p.profile_id = %s::uuid
          AND p.post_id IS NULL
    """
    row = query_db(query, (post_id, user_id, profile_id), True)
    return bool(row and row["reels"])


def count_facebook_reels_last_24h(page_id):
    """Envios de Reels já iniciados para a Página nas últimas 24 h (limite da Meta: 30).

    Conta envios de posts marcados como Reels, sucesso ou em dúvida, de qualquer
    perfil ligado à mesma Página. ponytail: conta o post marcado mesmo se a mídia
    acabou sendo imagem (conservador); trocar por marca no envio se ficar apertado."""
    query = f"""
        SELECT COUNT(*) AS total
        FROM public.publish_jobs job
        JOIN public.posts p ON p.id = job.post_id
        JOIN public.facebook_credentials fc ON fc.user_id = job.user_id
          AND fc.profile_id IS NOT DISTINCT FROM job.profile_id
        WHERE job.network = 'facebook'
          AND fc.page_id = %s
          AND job.status IN ('running', 'succeeded', 'unknown')
          AND job.external_started_at >= now() - interval '24 hours'
          AND {FACEBOOK_REELS_SQL}
    """
    row = query_db(query, (str(page_id),), True)
    return int(row["total"]) if row else 0


def get(user_id, post_id, profile_id):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            -- parent node
            SELECT id, text, created_at, updated_at, post_id, user_id, profile_id, 0 as depth,
                   network
            FROM posts
            WHERE id = %s AND user_id = %s AND profile_id = %s::uuid
              AND post_id IS NULL

            UNION ALL

            -- children nodes
            SELECT
                p.id, p.text, p.created_at, p.updated_at, p.post_id,
                p.user_id, p.profile_id, ph.depth + 1, ph.network
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
            WHERE p.user_id = %s AND p.profile_id = %s::uuid
        )
        SELECT
            ph.id,
            ph.text,
            ph.created_at - interval '3 hours' AS created_at,
            ph.updated_at - interval '3 hours' AS updated_at,
            ph.post_id,
            ph.depth,
            ph.network,
            COALESCE(
                array_agg(
                    -- duplicating because of LEFT JOINS
                    DISTINCT pp.product_id
                ) FILTER (WHERE pp.product_id IS NOT NULL),
                '{}'
            ) product_ids,
            -- subquery (sem DISTINCT): a ordem é a escolhida pelo usuário
            -- (display_order); DISTINCT sobre jsonb reordenaria por valor.
            -- jsonb por causa do psycopg3.
            COALESCE(
                (
                    SELECT array_agg(
                        jsonb_build_object(
                            'id', m.id,
                            'file_name', m.file_name,
                            'file_path', m.file_path,
                            'size', m.size,
                            'type', m.type
                        ) ORDER BY pm.display_order, m.id
                    )
                    FROM posts_medias pm
                    JOIN medias m ON m.id = pm.media_id
                    WHERE pm.post_id = ph.id
                ),
                '{}'
            ) medias,
            COALESCE(
                json_build_object(
                    'id', s.id,
                    'func', s.func,
                    'trigger', s.trigger,
                    'time', to_char(s.time, 'HH24:MI'),
                    'day_of_week', s.day_of_week,
                    'days_of_week', s.days_of_week,
                    'start_date', s.start_date,
                    'run_date', s.run_date
                ),
                '{}'::json
            ) scheduler
        FROM post_hierarchy ph
        LEFT JOIN posts_products pp ON ph.id = pp.post_id
        LEFT JOIN schedulers s ON s.post_id = ph.id
          AND s.user_id = ph.user_id
          AND s.profile_id IS NOT DISTINCT FROM ph.profile_id
        GROUP BY
            ph.id, ph.text, ph.created_at, ph.updated_at, ph.post_id,
            ph.depth, ph.network, pp.post_id, s.id
        ORDER BY ph.depth ASC
    """
    args = (post_id, user_id, profile_id, user_id, profile_id)
    parts = post_content_snapshot.apply_to_parts(
        query_db(query, args), post_content_snapshot.get()
    )
    # Nunca publica o mapa {"rede": "texto"} da IA: só o texto da rede.
    parts = [
        {**part, "text": unwrap_network_text(part.get("text"), part.get("network"))}
        for part in parts or []
    ]
    return post_link_redirects.rewrite_parts(parts, _active_publish_job_id())


def _active_publish_job_id():
    """Só há envio ativo se o scheduler já carregou o contexto; não importa o scheduler à toa."""
    context = sys.modules.get("shopee_bot.scheduler.publication_context")
    return context.active_publish_job_id() if context else None


def get_for_delete(user_id, post_id):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            SELECT id, user_id, profile_id, 0 AS depth
            FROM posts
            WHERE id = %s AND user_id = %s AND post_id IS NULL

            UNION ALL

            SELECT p.id, p.user_id, p.profile_id, ph.depth + 1
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
            WHERE p.user_id = %s AND p.profile_id IS NOT DISTINCT FROM ph.profile_id
        )
        SELECT
            ph.id,
            ph.depth,
            COALESCE(
                array_agg(
                    json_build_object(
                        'file_path', m.file_path
                    )
                ) FILTER (WHERE m.id IS NOT NULL),
                '{}'
            ) AS medias,
            COALESCE(
                json_build_object('id', s.id),
                '{}'::json
            ) scheduler
        FROM post_hierarchy ph
        LEFT JOIN posts_medias pm ON ph.id = pm.post_id
        LEFT JOIN medias m ON pm.media_id = m.id
        LEFT JOIN schedulers s ON s.post_id = ph.id
          AND s.user_id = ph.user_id
          AND s.profile_id IS NOT DISTINCT FROM ph.profile_id
        GROUP BY ph.id, ph.depth, s.id
        ORDER BY ph.depth;
    """
    args = (post_id, user_id, user_id)
    return query_db(query, args)


def query_paginated(user_id, cursor, limit):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            -- Seleciona os posts raiz (onde post_id é NULL)
            SELECT id, id AS root_id, profile_id, 0 AS depth
            FROM posts
            WHERE post_id IS NULL AND user_id = %s

            UNION ALL

            -- Seleciona os filhos recursivamente, mantendo o root_id
            SELECT p.id, ph.root_id, p.profile_id, ph.depth + 1
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
            WHERE p.user_id = %s AND p.profile_id IS NOT DISTINCT FROM ph.profile_id
        )
        SELECT
            p.id,
            p.text,
            p.created_at - interval '3 hours' AS created_at,
            p.updated_at - interval '3 hours' AS updated_at,
            COALESCE(
                array_agg(
                    json_build_object(
                        'id', m.id,
                        'file_name', m.file_name,
                        'file_path', m.file_path,
                        'size', m.size,
                        'type', m.type
                    ) ORDER BY pm.display_order, m.id
                ) FILTER (WHERE m.id IS NOT NULL),
                '{}'
            ) medias,
            (
                SELECT COUNT(*)
                FROM post_hierarchy ph
                WHERE ph.root_id = p.id AND ph.depth > 0
            ) children,
            COALESCE(
                json_build_object(
                    'id', s.id,
                    'func', s.func,
                    'trigger', s.trigger,
                    'time', s.time,
                    'day_of_week', s.day_of_week,
                    'days_of_week', s.days_of_week,
                    'start_date', s.start_date,
                    'run_date', s.run_date
                ),
                '{}'::json
            ) scheduler
        FROM posts p
        LEFT JOIN posts_medias pm ON p.id = pm.post_id
        LEFT JOIN medias m ON m.id = pm.media_id
        LEFT JOIN schedulers s ON s.post_id = p.id
          AND s.user_id = p.user_id
          AND s.profile_id IS NOT DISTINCT FROM p.profile_id
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                p.created_at < %s OR (
                    p.created_at = %s AND p.id < %s
                )
            )
        ) AND p.user_id = %s AND p.post_id IS NULL
        GROUP BY
            p.id,
            p.text,
            p.created_at,
            p.updated_at,
            pm.post_id,
            s.id
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT %s;
    """
    args = []

    if cursor:
        # cursor format "created_at,id"
        try:
            last_created_at, last_id = cursor.split(",")
            last_created_at = last_created_at.strip()
            last_id = int(last_id.strip())
            args = [
                user_id, user_id,
                last_created_at,
                last_created_at,
                last_created_at,
                last_id,
                user_id,
                limit
            ]
        except ValueError:
            # products, next_cursor
            return [], None
    else:
        # Primeira página
        args = [user_id, user_id, None, None, None, None, user_id, limit]

    # Executa a query
    medias = query_db(query, args)

    next_cursor = None
    if medias and len(medias) == limit:
        last_item = medias[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"
    return medias, next_cursor


def insert(user_id, post, open_conn=None):
    query = """
        INSERT INTO posts(user_id, post_id, text, network)
        VALUES(%s, %s, %s, %s)
        RETURNING id
    """
    args = (
        user_id,
        post["post_id"] if "post_id" in post else None,
        post["text"],
        post.get("network") or "threads"
    )
    return execute_db(query, args, open_conn)


def update(user_id, post_id, post, open_conn=None):
    query = """
        UPDATE posts
        SET post_id = %s, text = %s, updated_at = %s,
            network = COALESCE(%s, network)
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        post["post_id"] if "post_id" in post else None,
        post["text"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        post.get("network"),
        post_id,
        user_id
    )
    return execute_db(query, args, open_conn)


def delete(user_id, post_id, open_conn=None):
    query = """
        DELETE FROM posts
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (post_id, user_id)
    execute_db(query, args, open_conn)
