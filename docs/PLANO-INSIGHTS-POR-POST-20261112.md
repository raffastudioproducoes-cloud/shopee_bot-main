# Plano — métricas por postagem em todas as redes (Análises e Dashboard)

**Data:** 12/11/2026 · **Base auditada:** `origin/staging` @ `4a7218be` (VERSION 3.18.0) · **Tipo:** auditoria + plano, **sem implementação**. Nenhum código, migração, VERSION ou CHANGELOG alterado. Nenhuma API de rede, banco ou conta real foi acionada nesta rodada.

**Pedido do Rafa:** para cada post enviado a cada rede — visualizações, cliques, curtidas, comentários, compartilhamentos/recompartilhamentos — e ranking de qual **postagem** e qual **rede** teve melhor desempenho, não só o geral da rede.

Convenções: **Fato (código)** = lido no arquivo:linha citado. **Fato (doc)** = lido na página oficial citada nesta data. **Não confirmado** = não encontrado na página aberta (URL indicada). **Proposta** = recomendação deste plano.

---

## 1. Tabela resumo por rede

| Rede | Métricas por post na API oficial (doc) | Clique por post? | Permissão / requisito | Estado atual no código | Esforço | Bloqueio externo |
|---|---|---|---|---|---|---|
| **Threads** | `views`*, `likes`, `replies`, `reposts`, `quotes`, `shares`* (*"in development") | **Não.** `clicks` só existe em insights de **usuário**, por URL | `threads_basic` + `threads_manage_insights` | **Coletor existe** (`api/post_insights.py`), só 90 dias, sem histórico; sequências e IDs de confirmação manual ficam sem métrica | Baixo | Reconexão das contas com o escopo; App Review para usuários sem papel no app |
| **Instagram** | FEED: `views`, `reach`, `likes`, `comments`, `shares`, `saved`, `reposts`, `total_interactions`, `profile_visits`; REELS: + `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time`, `reels_skip_rate`; STORY: + `link_clicks`, `navigation` | **Só em Story** (`link_clicks`). Feed/Reels: não | FB Login: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`; IG Login: `instagram_business_basic`, `instagram_business_manage_insights`; conta profissional | Publicador grava `id` da mídia; **nenhum coletor** | Médio | App Review de `instagram_manage_insights`; conta profissional de teste |
| **Facebook (Página)** | `/{post-id}/insights`: `post_media_view`, `post_total_media_view_unique`, `post_reactions_by_type_total`, `post_video_views`, `post_clicks`, `post_clicks_by_type`; objeto Post: `shares.count`, edges `reactions`/`comments` | **Parcial.** `post_clicks` = todos os cliques, não isola link | `read_insights` + `pages_read_engagement`, token de Página com tarefa ANALYZE; Página com 100+ curtidas | Publicador grava `id` de foto/vídeo/feed sem normalizar; **nenhum coletor** | Médio-alto | App Review de `read_insights`; Página de teste com 100+ curtidas |
| **TikTok** | `view_count`, `like_count`, `comment_count`, `share_count` (máx. 20 IDs/req) | **Não** | `video.list` (OAuth atual só pede `user.info.basic,video.publish,video.upload`) | Publicador grava **`publish_id`**, não o ID do vídeo; posta `SELF_ONLY` | Médio | Auditoria do app TikTok (sem ela tudo fica privado e o `post_id` público não é devolvido) + escopo `video.list` |
| **X** | `public_metrics`: `impression_count`, `like_count`, `reply_count`, `retweet_count`, `quote_count`, `bookmark_count`; `non_public_metrics`: `url_link_clicks`, `user_profile_clicks` | **Sim** (`url_link_clicks`), só posts próprios com user context e **criados há até 30 dias** | OAuth 1.0a/2.0 user context | Publicação desabilitada por regra; grava só o último tweet da sequência | Baixo-médio | Regra de produto (X desabilitado) + plano/custo da X API (não confirmado) |
| **Telegram** | Bot API: nenhum campo/método de views encontrado; MTProto `stats.getBroadcastStats` retorna `recent_posts_interactions` (`views`, `forwards`, `reactions`) | **Não** | MTProto como **administrador** do canal, `can_view_stats`, tamanho mínimo do canal (valor não publicado) | **Sem publicador** | Alto | Decidir arquitetura MTProto (sessão de usuário), com risco de segurança |
| **WhatsApp** | Webhook de status por mensagem (`sent`, `delivered`, `read`); `template_analytics` diário por **template** (`sent`, `delivered`, `read`, `clicked` por botão URL) | **Só por template/dia**, não por mensagem; read/click só 7 dias | WABA + Cloud API; permissões não citadas na página aberta | **Sem publicador** | Alto | Conta WABA, templates aprovados, consentimento/LGPD |
| **Shopee Vídeo** | **Não confirmado** (doc Open Platform inacessível nesta rodada) | Não confirmado | Aprovação Video Management + OAuth próprio | Cliente isolado/bloqueado, sem publicador | Alto | Aprovação Shopee (ver `docs/SHOPEE-VIDEO-AFILIADOS-GATE-20261107.md`) |
| **Kwai** | **Nenhuma API de métricas** encontrada | Não | — | `apis/kwai.py` sem implementação; sem publicador | — | Sem API oficial; não implementar |
| **Link Shopee (todas)** | Cliques no link **não vêm das redes** | Affiliate API: **não confirmado**; redirecionador próprio: sim | — | Short link gerado **por produto** com `subIds=[product_id]` | Médio | Nenhum para o redirecionador; decisão de produto/LGPD |

---

## 2. Auditoria do código (o que existe hoje)

### 2.1 Coleta
- **Só Threads coleta métricas por post.** `collect_profile_posts` lê jobs com `network="threads"` (`api/post_insights.py:67`) e devolve `facebook/instagram="not_connected"`, `tiktok/x="unsupported"` fixos (`api/post_insights.py:151-180`).
- Endpoint: `GET graph.threads.net/v1.0/{id}/insights?metric=views,likes,replies,reposts,quotes,shares`, com fallback só para `views` em HTTP 400 (`api/post_insights.py:19-21,103-130`). 401/403 vira `permission_required` (`:116`).
- Janela: só jobs dos **últimos 90 dias** (`api/post_insights.py:61`). Posts mais antigos deixam de ser atualizados.
- O ID externo precisa casar `^[0-9]{1,40}$` (`api/post_insights.py:22,105`). Consequência: (a) a confirmação manual grava o **permalink** HTTPS em `external_id` (`api/routers/posts.py:1162`) e vira `invalid_id`; (b) IDs de feed do Facebook no formato `{page}_{post}` seriam rejeitados se o mesmo validador for reaproveitado.
- Sequências Threads ficam `multipart_unmapped` (`api/post_insights.py:77-89,168-169`) porque o publicador grava só o **último** ID (`scheduler/bot_post.py:152`).
- Agendamento: job APScheduler **a cada 1 hora** (`scheduler/__init__.py:452-459,544-545`) que processa até **12 perfis** com última tentativa há mais de 24 h (`api/analytics_refresh.py:73-92`). Manual: claim de 5 min e cota de 10/dia/conta (`api/analytics_refresh.py:17-39`, migração 092).
- Persistência: `upsert` por `publish_job_id` **sobrescreve** a linha (`api/post_insights.py:133-144`). **Não há histórico** de coletas; não existe "views em 24 h / 7 d", só o total lifetime da última coleta.
- Escopos OAuth: Threads já inclui `threads_manage_insights` (`api/threads_oauth.py:32-33`). Facebook pede `pages_show_list, pages_manage_posts, pages_read_engagement` (`api/meta_pages.py:17`), **sem `read_insights`**. TikTok pede `user.info.basic,video.publish,video.upload` (`apis/tiktok.py:74`, `api/tiktok_oauth.py:36`), **sem `video.list`**.

### 2.2 Tabela de insights
- `public.publication_insights` (`database/migrations/088_publication_insights.sql:4-27`): PK `publish_job_id`, `user_id`, `profile_id`, `network` com CHECK só para `threads, facebook, instagram, tiktok, x` (`:8`), colunas `views, likes, comments, reposts, shares, quotes, clicks`, `state`, `last_attempt_at`, `last_completed_at`. RLS ligado, grants só para `service_role` (`:23-25`).
- Faltam: `reach`, `saves`, `watch_time`, `extra`, `source`, código de erro, histórico e as redes telegram/whatsapp/shopee_video/kwai.
- Estado de refresh por perfil: `analytics_daily_refreshes` (migrações 064/065/092).

### 2.3 Como o `external_id` é guardado (`publish_jobs.external_id TEXT`, `database/migrations/053_create_publish_jobs.sql:19`)

| Rede | Valor gravado | Fonte | Problema para métricas |
|---|---|---|---|
| Threads | ID numérico do **último** post da sequência | `scheduler/bot_post.py:152` | Partes sem ID; confirmação manual grava URL (`api/routers/posts.py:1162`) |
| X | ID do **último** tweet da sequência | `scheduler/bot_post_x.py:186` | Igual ao Threads |
| Facebook | `external_id()` pega `id`, depois `post_id`, depois `media_id` da resposta (`scheduler/publication_result.py:25-28`, `scheduler/bot_post_facebook.py:168`) | `/feed` (`apis/facebook.py:197`), `/photos` (`:215`), `/videos` (`:258`) | Em `/photos` o `id` tende a ser da **foto**, não do post; em `/feed`, do post; em `/videos`, do vídeo. São objetos diferentes. Forma exata das respostas: **não conferida** nesta rodada |
| Instagram | `id` da mídia publicada (`scheduler/bot_post_instagram.py:133`) | `media_publish` | Carrossel: insights só do álbum; filhos não têm |
| TikTok | **`publish_id`** (`scheduler/bot_post_tiktok.py:164`) | Content Posting API | **Não é o ID do vídeo.** `video/query` precisa do ID do vídeo, que só aparece em `publicaly_available_post_id` quando o post é público |
| Telegram / WhatsApp / Shopee Vídeo / Kwai | — | Não há publicador (`scheduler/__init__.py:84-91` só registra 5 redes) | Não há "post enviado" para medir |

### 2.4 API de leitura
- `GET /analytics/summary`, `/analytics/posts`, `/analytics/timeline`, `POST /analytics/refresh`, `GET /analytics/refresh/quota` (`api/routers/social_analytics.py`).
- Filtros: `days` só `7|30|90` (`:190,262,324`), `network` Literal de 5 redes (`:21-22`), `profile_id` = `all` ou UUID com ownership validada (`:27-44`).
- `summary` **força `null`** nas métricas de qualquer rede que não seja Threads (`:231-233`).
- `posts` devolve até 150 posts ordenados **apenas por `views`** (`:304-307`). Não há ranking por outra métrica, nem por rede, nem taxa de engajamento.
- O período filtra a **data de publicação**; as métricas são lifetime (`:248-249`).

### 2.5 UI
- `AnalyticsPage.tsx`: filtros **Perfil** (todos/individual), **Período** (7/30/90), **Rede** (9 do catálogo; 4 sem backend mostram aviso e não chamam API) (`frontend/src/pages/AnalyticsPage.tsx:172-185,100-101,215-221`; `frontend/src/lib/analyticsNetworks.ts:4,10-20`).
- `AnalyticsVisuals.tsx`: 6 KPIs e 6 painéis. **Ranking** = `TopPosts`, top **5** por views (`frontend/src/components/AnalyticsVisuals.tsx:281-315`), sem compartilhamentos/saves no card. Não há "melhor rede" por desempenho: `NetworkComparison` compara **volume de envios** (`:182-222`).
- `DashboardPage.tsx`: **nenhuma métrica de rede**, só contadores de produtos/posts/listas/agendas e listas recentes (`frontend/src/pages/DashboardPage.tsx:55-96`; backend `api/routers/dashboard.py:72-111`).

### 2.6 Respostas diretas
- **Existe coleta por post?** Só Threads. Facebook, Instagram, TikTok, X: não. Telegram, WhatsApp, Shopee Vídeo, Kwai: nem publicação existe.
- **Qual tabela guarda?** `publication_insights` (uma linha por job, sem histórico).
- **Existe ranking?** Só de posts por visualizações (top 5 na UI, 150 na API). Ranking de rede por desempenho: não.
- **O que a UI filtra?** Rede, perfil e período (7/30/90).

### 2.7 Link de afiliado
- O short link é gerado **por produto**, uma vez, com `subIds: [product_id]` (`apis/shopee.py:134-150,177`) e salvo em `products.commission_link`. O mesmo link vai para todos os posts e redes. Mesmo que a Shopee informe cliques por sub-ID, hoje não dá para separar por post nem por rede.

---

## 3. Pesquisa oficial por rede (consultada em 12/11/2026)

### Threads — https://developers.facebook.com/docs/threads/insights/
- `GET /{threads-media-id}/insights?metric=...`. Métricas de mídia: `views` (in development), `likes`, `replies` (no post raiz, total de respostas; numa resposta, só as diretas), `reposts`, `quotes`, `shares` (in development).
- `clicks` **não é métrica de mídia**: só aparece nos insights de usuário, por URL. **Threads não fornece clique por post.**
- Permissões: `threads_basic` + `threads_manage_insights`. Posts `REPOST_FACADE` retornam vazio. `since/until` não funciona antes de 13/04/2024. Atraso de processamento: **não confirmado** na página.

### Instagram — https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights
- `GET /{ig-media-id}/insights` em `graph.facebook.com` (Facebook Login) ou `graph.instagram.com` (Instagram Login). A página indica v27.0; o código usa v26.0 (`apis/meta_version.py:13`).
- FEED: `comments, facebook_views, follows, likes, profile_activity, profile_visits, reach, reposts, saved, shares, total_interactions, views` (mais `total_*` só com FB Login). `impressions` depreciado para mídia criada após 02/07/2024.
- REELS: mais `ig_reels_avg_watch_time, ig_reels_video_view_total_time, reels_skip_rate, crossposted_views`.
- STORY: mais `link_clicks, navigation, replies`. Disponível só por **24 h**; stories com menos de 5 visualizadores retornam erro 10.
- Filhos de álbum **não têm** insights. Dado indisponível volta vazio (não zero). Atraso de até **48 h**. Retenção de 2 anos. `likes/comments/views` são orgânicos.
- Permissões: FB Login `instagram_basic, instagram_manage_insights, pages_read_engagement`; IG Login `instagram_business_basic, instagram_business_manage_insights`. A página fala em conta profissional sem detalhar; mídia anterior à conversão da conta: **não confirmado**.
- **Clique por post: só `link_clicks` em Story.** Feed/Reels: não.

### Facebook Página — https://developers.facebook.com/docs/graph-api/reference/insights/ e https://developers.facebook.com/docs/graph-api/reference/post/
- `/{post-id}/insights`: `post_media_view`, `post_total_media_view_unique`, `post_reactions_by_type_total`, `post_video_views` (3 s ou mais), `post_clicks`, `post_clicks_by_type`. `post_impressions*` marcado obsoleto acima da v25. A página avisa que até 15/06/2026 "várias métricas" de Page Insights seriam depreciadas em todas as versões, sem listar quais: **confirmar a lista antes de implementar**.
- Requisitos: `read_insights` + `pages_read_engagement`, token de Página de quem tem a tarefa ANALYZE, Página com **100 ou mais curtidas**, atualização a cada ~24 h, 2 anos de retenção.
- Objeto Post: `shares.count`; reações e comentários como edges. `reactions.summary`/`comments.summary` **não descritos** na página aberta.
- **Clique em link por post: não existe.** `post_clicks` conta todos os cliques que não geram story; a página não confirma se `post_clicks_by_type` separa cliques em link.
- Formato `{page}_{post}` e relação foto/post: **não confirmado** na página do Post.

### TikTok — https://developers.tiktok.com/doc/tiktok-api-v2-video-query · https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status · https://developers.tiktok.com/doc/content-posting-api-get-started
- `POST https://open.tiktokapis.com/v2/video/query/`, escopo `video.list`, até 20 IDs, campos `view_count, like_count, comment_count, share_count` (mais `duration`, `share_url`). Só vídeos do usuário autorizado. **Sem clique.** Rate limit e vídeos privados: **não confirmado**.
- `status/fetch` devolve `publicaly_available_post_id` **só para posts públicos** aprovados na moderação; também existe o webhook `post.publish.publicly_available`.
- Doc: "All content posted by unaudited clients will be restricted to private viewing mode." Com app não auditado e `SELF_ONLY` padrão (`apis/tiktok.py:421`), **o ID público não é devolvido**, logo não há como chamar `video/query`. Se `video/list` inclui vídeos privados: **não confirmado**.

### X — https://docs.x.com/x-api/fundamentals/metrics
- `public_metrics` (qualquer auth): `impression_count, like_count, reply_count, retweet_count, quote_count, bookmark_count`.
- `non_public_metrics`/`organic_metrics` (user context, só posts próprios, **criados há até 30 dias**): `url_link_clicks, user_profile_clicks, engagements`.
- **Única rede com clique em link por post**, limitado a 30 dias. Plano/preço da X API: **não confirmado**.

### Telegram — https://core.telegram.org/api/stats · https://core.telegram.org/bots/api
- MTProto: `stats.getBroadcastStats` retorna `recent_posts_interactions` (`msg_id, views, forwards, reactions`); `stats.getMessageStats` devolve **grafos**. Exige admin do canal, `can_view_stats` e tamanho mínimo do canal (não publicado).
- Bot API: nos primeiros 100 mil caracteres lidos, `Message` **não tem `views`** e não há método de views. Bot admin recebe `message_reaction_count` (reações anônimas, com atraso de minutos) se pedir em `allowed_updates`. O restante da página não foi lido: ausência de método de views **parcialmente confirmada**.
- **Clique por post: não.**

### WhatsApp — https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples · https://developers.facebook.com/docs/whatsapp/business-management-api/analytics
- Por mensagem: só status `sent`, `delivered`, `read` via webhook. Sem views, curtidas ou cliques.
- `template_analytics`: diário, **por template** (até 10 por request), 90 dias, `clicked` por botão `url_button`/`unique_url_button` (só templates MARKETING/UTILITY), read/click disponíveis por 7 dias. Exige `is_enabled_for_insights=true` (irreversível). Permissões: **não citadas** na página.
- WhatsApp Channels/Status: **não coberto** pela doc aberta.

### Shopee Vídeo
- https://open.shopee.com/documents/v2/v2.video.get_video_detail?module=129&type=1 — **inacessível** à ferramenta nesta rodada. Campos de métrica: **não confirmado**. Valem os gates de `docs/SHOPEE-VIDEO-AFILIADOS-GATE-20261107.md`.

### Kwai — https://www.kwai.com/support/creator-center
- Nenhuma API de métricas para criadores na página. **Não implementar** (sem scraping).

### Cliques no link Shopee
- https://affiliate.shopee.com.br/open_api devolveu só o título, sem documentação. Se a Affiliate API dá **cliques** (e não só conversões) por `subId`/short link: **não confirmado**. O código já usa `generateShortLink(originUrl, subIds)` (`apis/shopee.py:137-141`), o que mostra que `subIds` existe na entrada; relatórios por sub-ID não foram verificados.
- **Proposta (independe da Shopee):** redirecionador próprio `GET /r/{token}` com 302 para o `commission_link`, um token opaco por `publish_job_id` e contagem de cliques. É o único jeito de ter **cliques por post e por rede em todas as redes**. Requisitos: token aleatório sem PII; destino só do banco (sem open redirect); contador agregado sem IP/UA guardados; filtro de bots e de pré-visualização de link (crawlers contam como clique se não filtrados); rate limit; domínio próprio. Ressalva: no Instagram o link na legenda não é clicável, então o rastreio vale onde o link é clicável. Complemento opcional: short link Shopee com `subIds` por envio/rede, para cruzar conversões quando a doc de relatórios for confirmada.

---

## 4. Plano de estrutura

### 4.1 Modelo de dados (migrações **aditivas**, compatíveis com o banco compartilhado staging/produção)
- **Manter `publication_insights`** como "último valor" (já lido pela API/UI). Migração aditiva: `reach, saves, watch_time_ms BIGINT NULL`, `extra JSONB NOT NULL DEFAULT jsonb_build_object()`, `source TEXT`, `error_code TEXT`; trocar o CHECK de `network` por lista com `telegram, whatsapp, shopee_video, kwai` (DROP/ADD CONSTRAINT `NOT VALID` + `VALIDATE`, sem reescrita de tabela).
- **Nova `post_metric_snapshots`** (histórico de coletas): `id BIGSERIAL`, `publish_job_id UUID FK ON DELETE CASCADE`, `user_id`, `profile_id`, `network`, `external_id`, `collected_at`, `age_bucket` (`1h|24h|7d|30d|manual`), `views, reach, likes, comments, shares, saves, clicks, link_clicks BIGINT NULL`, `extra JSONB`, `source TEXT` (`threads_media_insights`, `ig_media_insights`, `fb_post_insights`, `tiktok_video_query`, `x_tweet_lookup`, `redirect`), `status` (`ok|no_data|permission_required|token_expired|rate_limited|invalid_id|api_error`), `error_code` sanitizado. Índices `(user_id, profile_id, network, collected_at)` e `(publish_job_id, collected_at)`. RLS ligado, grants só `service_role` (igual ao 088). Sem resposta bruta, sem token.
- **Nova `publish_job_external_parts`**: `publish_job_id, part_index, external_id`, para guardar os IDs de todas as partes das sequências Threads/X e eliminar `multipart_unmapped`. Métrica do post = soma das partes, com detalhe em `extra.parts`.
- **Nova `link_clicks`**: `token TEXT PK`, `publish_job_id`, `user_id`, `profile_id`, `network`, `clicks BIGINT`, `last_click_at`, mais agregado diário `(token, day, clicks)`. Sem IP/UA persistidos.
- Coluna aditiva `publish_jobs.external_kind TEXT NULL` (`post|photo|video|reel|story|carousel|tiktok_publish`) para escolher o endpoint certo de cada rede.

### 4.2 Coletor por rede
- Uma função por rede com o mesmo contrato `collect(client, job, credential) -> (status, metrics, extra)`, registradas num dicionário rede-para-função em `api/post_insights.py` (sem classes nem fábricas).
- Normalização para as colunas comuns; ausente = `NULL`, nunca 0; o específico (`quotes`, `reels_skip_rate`, `post_reactions_by_type_total`) vai em `extra`.
- Resolver o ID antes de coletar: Threads/X, todas as partes; Facebook, normalizar foto/vídeo/feed para o objeto certo (confirmar na doc); TikTok, `status/fetch` ou webhook para gravar `publicaly_available_post_id`.
- Agendamento: reusar o job APScheduler horário (`scheduler/__init__.py:544`). Elegibilidade por idade do post: **1 h, 24 h, 7 d, 30 d** após `finished_at`; depois disso, só no refresh manual. Trocar o corte fixo de 90 dias por "último snapshot em 30 d + manual". X: `non_public_metrics` só até 30 dias.
- Erros: 401/403 viram `permission_required`/`token_expired` e não há nova tentativa até reconectar; 429 vira `rate_limited` com backoff até a próxima janela; 5xx/timeout tentam de novo na execução seguinte. Concorrência por rede limitada (já existe `_PARALLEL=4`). Logs sem token e sem corpo bruto.

### 4.3 API de leitura (estender, não substituir)
- `GET /analytics/posts`: `sort=views|likes|comments|shares|saves|clicks|engagement`, `limit` (até 150), mantendo `network`, `profile_id`, `days`. Devolver todas as métricas comuns, `extra` filtrado e `collected_at`.
- `GET /analytics/posts/{job_id}`: detalhe com a série de snapshots (1 h / 24 h / 7 d / 30 d).
- `GET /analytics/ranking?metric=...&by=post|network&top=N`: ranking de posts e de **redes** (total e média por post, só com posts que têm a métrica, sempre com o `n` de posts medidos, para não comparar rede com 1 post contra rede com 50).
- `summary`: remover o forçamento de `null` das redes não-Threads (`social_analytics.py:231-233`) **somente** quando o coletor da rede existir.
- Ampliar o Literal `Network` para as 9 redes só quando houver publicador/coletor de cada uma.

### 4.4 UI
- **Análises:** tabela por post (rede, perfil, data, prévia, views, curtidas, comentários, compartilhamentos, saves, cliques, estado da coleta) com ordenação por coluna e paginação; cards "Melhor post" e "Melhor rede" pela métrica escolhida; seletor de métrica do ranking; traço = indisponível; tooltip com a fonte ("cliques: redirecionador Auto Orbital", "Instagram: até 48 h de atraso"). Detalhe do post com evolução 1 h / 24 h / 7 d / 30 d.
- **Dashboard:** painel "Top 3 posts (7 dias)" e "Melhor rede (7 dias)" via `/analytics/ranking`, sem recalcular no front.
- Manter os filtros atuais (perfil, período, rede) e o aviso das redes sem integração.

### 4.5 Segurança e LGPD
- Toda leitura com `scope_account`/`scope_owner` e validação de ownership do perfil (já existe em `_analytics_profile`). Tabelas novas com RLS e grants só `service_role`.
- Tokens decifrados só no servidor; nunca em log, `extra` ou resposta.
- Métricas de post são agregadas. **Não** coletar quem curtiu/comentou, demografia nem dados de destinatários do WhatsApp. Redirecionador sem IP/UA persistidos.
- Exclusão de conta: `ON DELETE CASCADE` a partir de `publish_jobs`/`users`; incluir as tabelas novas no fluxo de erasure (migrações 081-086).
- Política de privacidade: mencionar a contagem de cliques do redirecionador.

### 4.6 Testes
- Unitários de parser por rede com fixtures baseadas na doc (ausente diferente de 0, duplicata, tipo de mídia, erro 10 de Story, `REPOST_FACADE`).
- Resolução de ID (sequência, foto/post, `publish_id` para ID público).
- Isolamento 2 contas x 2 perfis em `posts`, `ranking` e `posts/{job_id}`.
- Migração em banco limpo e sobre o estado de staging (aditiva, idempotente).
- Redirecionador: token inválido 404, sem open redirect, bots filtrados, rate limit.
- Front: ordenação, empate, traço, ranking de rede com `n` pequeno.

---

## 5. Fases (por valor e dependência externa)

**Fase 1 — sem nova aprovação externa**
1. Migração aditiva: colunas novas em `publication_insights`, `post_metric_snapshots`, `publish_job_external_parts`.
2. Threads completo: gravar IDs de todas as partes; tratar o permalink da confirmação manual (resolver para ID ou marcar sem métrica); snapshots 1 h / 24 h / 7 d / 30 d; estados `token_expired`/`rate_limited`.
3. API: `sort`, `ranking` por post e por rede, detalhe do post.
4. UI: tabela por post, ranking, melhor post/rede, painel no Dashboard.
5. Redirecionador de cliques próprio (único caminho de clique por post em todas as redes). Entra na Fase 1 se o Rafa aprovar domínio e texto de privacidade; senão, Fase 2.

**Fase 2 — Instagram e Facebook** (App Review Meta + contas de teste)
- Instagram: `/{media-id}/insights` por tipo de mídia; carrossel só no álbum.
- Facebook: normalizar o ID; `/{post-id}/insights` com métricas não depreciadas + `shares`/reações; pedir `read_insights`.

**Fase 3 — TikTok** (auditoria do app + `video.list`)
- Capturar `publicaly_available_post_id` (poll ou webhook) e coletar via `video/query` em lotes de 20.

**Fase 4 — X** (reativação da rede + plano de API)
- `public_metrics` + `non_public_metrics` (até 30 dias) para cliques em link.

**Fase 5 — Telegram, WhatsApp, Shopee Vídeo** (antes, precisam de publicador)
- Telegram: só com decisão sobre MTProto; Bot API não tem views. Cliques via redirecionador.
- WhatsApp: status por mensagem + `template_analytics` por template/dia; cliques via redirecionador.
- Shopee Vídeo: só após aprovação e confirmação dos campos.
- **Kwai:** fora do plano enquanto não houver API oficial.

---

## 6. Bloqueios e ações do Rafa (por rede)

| Rede | O que depende do Rafa |
|---|---|
| Threads | Reconectar as contas de teste (o escopo `threads_manage_insights` só entra numa nova autorização). Enviar a permissão para App Review **depois** que a Fase 1 estiver em staging, com gravação de tela da Análises mostrando a métrica. |
| Instagram | Conta **profissional** de teste ligada a uma Página; escolher Facebook Login ou Instagram Login; App Review de `instagram_manage_insights` (ou `instagram_business_manage_insights`) **após** o leitor existir. |
| Facebook | Página de teste com **100 ou mais curtidas**; incluir `read_insights` na configuração do `FACEBOOK_CONFIG_ID`; App Review **após** o leitor existir. |
| TikTok | Submeter o app à **auditoria** do Content Posting (sem ela os posts ficam privados e sem ID público); pedir o escopo `video.list`; decidir a privacidade padrão das publicações. |
| X | Decidir se X volta a ser habilitado; plano/custo da X API. |
| Telegram | Decidir se aceita sessão MTProto de usuário administrador (risco) ou fica só com os cliques do redirecionador. |
| WhatsApp | Conta WABA, número, templates aprovados, base de consentimento. |
| Shopee Vídeo | Aprovação do Video Management (gate existente). |
| Link Shopee | Aprovar o redirecionador próprio (domínio, texto de privacidade); fornecer acesso à documentação da Affiliate Open API (a página pública não mostra relatórios). |

**Texto de uso por permissão (enviar só depois que o leitor existir e estiver visível em staging):**
- `threads_manage_insights`: "O Auto Orbital publica no Threads os posts que o próprio usuário cria e agenda. Usamos esta permissão apenas para ler visualizações, curtidas, respostas, reposts, citações e compartilhamentos **dos posts publicados pelo app**, exibidos ao próprio usuário na página Análises para comparar o desempenho entre seus posts. Não lemos insights de terceiros e não compartilhamos os dados."
- `instagram_manage_insights`: "Lemos insights apenas das mídias publicadas pelo Auto Orbital na conta profissional do próprio usuário (visualizações, alcance, curtidas, comentários, compartilhamentos, salvamentos) para exibi-los a ele na página Análises, com ranking das suas publicações. Não coletamos dados de seguidores individuais."
- `read_insights` (com `pages_read_engagement`): "Lemos métricas dos posts que o Auto Orbital publicou na Página administrada pelo usuário (visualizações de mídia, reações, compartilhamentos, cliques) para mostrar a ele o desempenho de cada post. Não usamos métricas gerais da Página como se fossem do post."
- `video.list` (TikTok): "Lemos visualizações, curtidas, comentários e compartilhamentos somente dos vídeos que o usuário publicou pelo Auto Orbital, para exibi-los na página Análises dele."

---

## 7. Fontes oficiais abertas nesta rodada
- https://developers.facebook.com/docs/threads/insights/
- https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights
- https://developers.facebook.com/docs/graph-api/reference/insights/
- https://developers.facebook.com/docs/graph-api/reference/post/
- https://developers.tiktok.com/doc/tiktok-api-v2-video-query
- https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status
- https://developers.tiktok.com/doc/content-posting-api-get-started
- https://docs.x.com/x-api/fundamentals/metrics
- https://core.telegram.org/api/stats
- https://core.telegram.org/bots/api (lida parcialmente)
- https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
- https://developers.facebook.com/docs/whatsapp/business-management-api/analytics
- https://www.kwai.com/support/creator-center
- https://affiliate.shopee.com.br/open_api (sem conteúdo de documentação)
- https://open.shopee.com/documents/v2/v2.video.get_video_detail?module=129&type=1 (inacessível)
