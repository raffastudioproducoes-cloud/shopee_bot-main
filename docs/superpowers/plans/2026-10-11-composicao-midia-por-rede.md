# Composição de Mídia por Rede Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Permitir que um único envio multi-rede publique a composição de mídia compatível por plataforma, sem uma incompatibilidade cancelar as demais.

**Architecture:** Um planejador puro calcula MediaPlan por rede usando regras espelhadas no frontend e no backend. Arquivos são enviados uma vez para o escopo do usuário/perfil antes de criar posts; a criação anexa a seleção de cada plano ao post da respectiva rede. O frontend orienta e permite ajuste; o backend recalcula a decisão e os publicadores executam somente o modo aprovado.

**Tech Stack:** Python 3, FastAPI, Pydantic, Supabase, React 19, TypeScript, TanStack Query, Flask scheduler, Cloudinary, pytest, Vite e Playwright.

**Spec:** docs/superpowers/specs/2026-10-11-composicao-midia-por-rede-design.md

## Global Constraints

- Uma rede incompatível nunca cancela a criação ou publicação das demais.
- Não truncar, substituir, reordenar ou remover arquivos silenciosamente.
- Usar text_only apenas quando a API da rede aceitar texto sem mídia; do contrário devolver blocked_reason e não criar post para aquela rede.
- Toda leitura, upload, preview, vínculo e exclusão de mídia filtra user_id e profile_id.
- Tokens, segredos, URLs assinadas e respostas brutas de provedores nunca entram na interface, testes, logs ou documentação.
- Kwai continua fora. Vídeo só é marcado como pronto após teste real aprovado por plataforma.
- Não alterar contratos legados de edição de post em uma única etapa.

## Review Focus

- Um media_id de outro perfil não pode aparecer no preview nem ser anexado, mesmo sob o mesmo user_id.
- Cinco fotos para X não podem virar quatro silenciosamente: devem cair no fallback, preservando os cinco arquivos para redes compatíveis.
- TikTok e Instagram não podem receber text_only quando a API oficial exigir mídia; devem ficar bloqueados somente naquela rede.
- Cancelar um rascunho remove apenas ativos temporários próprios, sem apagar mídia anexada a outro post.
- Uma falha remota depois da confirmação registra rede e causa sem vazar credencial e sem repetir publicações já concluídas.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| api/media_composition.py | Regras puras e modelo MediaPlan do servidor. |
| api/network_limits.py | Capacidades oficiais de mídia e publicação textual. |
| api/routers/posts.py | Upload temporário, preview, criação por plano e limpeza segura. |
| database/migrations/045_add_temporary_media.sql | Estado e expiração de ativo antes do vínculo. |
| frontend/src/lib/networkLimits.ts | Espelho tipado das capacidades. |
| frontend/src/lib/mediaComposition.ts | Planejador puro da interface. |
| frontend/src/components/posts/MediaVariantTabs.tsx | Abas dinâmicas e resumo da composição. |
| frontend/src/pages/PostsPage.tsx | Upload único, preview, confirmação e envio em lote. |
| frontend/src/api/posts.ts | Tipos e chamadas dos contratos de mídia. |
| apis/{facebook,instagram,x,tiktok}.py | Chamadas de foto e carrossel aceitas por cada API. |
| scheduler/bot_post_{facebook,instagram,x,tiktok}.py | Execução do modo da rede. |
| tests/api/test_media_composition.py | Matriz do planejador e fallback. |
| tests/api/test_posts_media_drafts.py | API, escopo, limpeza e criação em lote. |

## Task 1: Planejador de compatibilidade e capacidades oficiais

**Files:**
- Create: api/media_composition.py
- Modify: api/network_limits.py
- Modify: frontend/src/lib/networkLimits.ts
- Create: frontend/src/lib/mediaComposition.ts
- Test: tests/api/test_media_composition.py

**Interfaces:**
- Consumes: mídia com id, file_name, size e type, além de textos já escolhidos por rede.
- Produces: MediaPlan(network, mode, media_ids, text_variant, warnings, blocked_reason).

- [ ] **Step 1: Escrever testes que falham para modos e fallback**

    def test_five_images_for_x_falls_back_without_mutating_ids():
        plan = plan_network_composition("x", ["copy"], images(5), 0)
        assert plan.mode == "text_only"
        assert plan.media_ids == []
        assert "máx. 4" in plan.warnings[0]

    def test_tiktok_without_text_only_is_blocked():
        plan = plan_network_composition("tiktok", ["copy"], invalid_photo(), 0)
        assert plan.mode == "blocked"
        assert plan.blocked_reason

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/api/test_media_composition.py -q
Expected: FAIL porque api.media_composition não existe.

- [ ] **Step 3: Implementar o planejador mínimo**

    @dataclass(frozen=True)
    class MediaPlan:
        network: str
        mode: Literal["none", "single_image", "carousel", "video", "text_only", "blocked"]
        media_ids: list[int]
        text_variant: list[str]
        warnings: list[str]
        blocked_reason: str | None = None

    def plan_network_composition(network, texts, medias, product_count=0):
        issues = validate_post(network, texts, medias, product_count)
        errors = [issue["message"] for issue in issues if issue["level"] == "error"]
        if errors and NETWORK_RULES[network]["supports_text_only"]:
            return MediaPlan(network, "text_only", [], texts, errors)
        if errors:
            return MediaPlan(network, "blocked", [], texts, errors, errors[0])
        return compatible_plan(network, texts, medias)

Adicionar supports_text_only às tabelas de regras depois de cruzar cada chamada com a documentação oficial atual, nunca por inferência visual.

- [ ] **Step 4: Validar**

Run: pytest tests/api/test_network_limits.py tests/api/test_media_composition.py -q
Expected: PASS para imagem, carrossel, GIF, vídeo, tamanho, mistura, texto longo e rede sem texto-only.

- [ ] **Step 5: Commit**

    git add api/media_composition.py api/network_limits.py frontend/src/lib/networkLimits.ts frontend/src/lib/mediaComposition.ts tests/api/test_media_composition.py
    git commit -m "feat: planeja composição de mídia por rede"

## Task 2: Upload temporário seguro e preview no backend

**Files:**
- Create: database/migrations/045_add_temporary_media.sql
- Modify: api/routers/posts.py
- Test: tests/api/test_posts_media_drafts.py
- Test: tests/api/test_profile_scope_posts.py

**Interfaces:**
- Consumes: POST /posts/media multipart e POST /posts/preview-composition.
- Produces: ativos temporários pertencentes ao usuário/perfil e lista de MediaPlan sem gravar posts ou jobs.

- [ ] **Step 1: Escrever testes de ownership, expiração e preview**

    def test_preview_rejects_media_from_another_profile(client_for_profile_b):
        response = client_for_profile_b.post("/posts/preview-composition", json=payload_with_profile_a_media())
        assert response.status_code == 404

    def test_draft_media_has_no_link_until_batch_create(client):
        media = upload_draft(client, "foto.jpg")
        assert posts_medias_for(media["id"]) == []

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/api/test_posts_media_drafts.py tests/api/test_profile_scope_posts.py -q
Expected: FAIL porque endpoints e migração ainda não existem.

- [ ] **Step 3: Criar migração aditiva e armazenamento temporário**

    alter table public.medias add column if not exists temporary boolean not null default false;
    alter table public.medias add column if not exists expires_at timestamp;
    create index if not exists idx_medias_temporary_expiry
      on public.medias (user_id, profile_id, expires_at) where temporary = true;

Gravar rascunhos em web/media/drafts/<uuid>. Implementar limpeza que só remove temporários expirados sem posts_medias e sempre filtra dono e perfil. Chamar no upload e no cancelamento. Não alterar o trigger legado de órfãos.

- [ ] **Step 4: Criar contratos**

    @router.post("/media", status_code=201)
    async def upload_draft_media(file: UploadFile, user_id=Depends(...), profile_id=Depends(...)):
        return await store_media(file, user_id, profile_id, temporary=True)

    @router.post("/preview-composition")
    async def preview_composition(body: CompositionPreviewBody, user_id=Depends(...), profile_id=Depends(...)):
        medias = get_owned_medias(user_id, body.media_ids, profile_id)
        return {"plans": [plan_network_composition(n, body.texts_by_network[n], medias, len(body.product_ids)) for n in body.networks]}

Reutilizar magic bytes, caminho seguro e limite atual do endpoint legado.

- [ ] **Step 5: Validar**

Run: pytest tests/api/test_posts.py tests/api/test_network_limits.py tests/api/test_media_composition.py tests/api/test_posts_media_drafts.py tests/api/test_profile_scope_posts.py -q
Expected: PASS sem leitura entre perfis nem arquivo fora de MEDIA_ROOT.

- [ ] **Step 6: Commit**

    git add database/migrations/045_add_temporary_media.sql api/routers/posts.py tests/api/test_posts_media_drafts.py tests/api/test_profile_scope_posts.py
    git commit -m "feat: adiciona mídia temporária por perfil"

## Task 3: Criação multi-rede a partir do plano confirmado

**Files:**
- Modify: api/routers/posts.py
- Modify: frontend/src/api/posts.ts
- Test: tests/api/test_posts_media_drafts.py
- Test: tests/api/test_posts_network_routing.py

**Interfaces:**
- Consumes: POST /posts/batch com redes, textos por rede, mídia por rede, produtos, agendamento e group_id.
- Produces: resultado por rede com created, text_only ou blocked.

- [ ] **Step 1: Escrever teste de criação parcial**

    def test_batch_creates_threads_with_media_and_x_text_only(client):
        response = client.post("/posts/batch", json=batch_payload(
            media_ids_by_network={"threads": [10, 11], "x": []},
            texts_by_network={"threads": ["copy"], "x": ["copy"]},
        ))
        assert response.status_code == 201
        assert post_media_ids("threads") == [10, 11]
        assert post_media_ids("x") == []
        assert response.json()["results"]["x"]["mode"] == "text_only"

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/api/test_posts_media_drafts.py::test_batch_creates_threads_with_media_and_x_text_only -q
Expected: FAIL porque /posts/batch não existe.

- [ ] **Step 3: Implementar criação isolada por rede**

    for network in body.networks:
        plan = plan_network_composition(network, body.texts_by_network[network], owned_media[network], len(body.product_ids))
        if plan.mode == "blocked":
            results[network] = {"status": "blocked", "reason": plan.blocked_reason}
            continue
        head = create_thread(user_id, plan.text_variant, network, profile_id, str(group_id))
        attach_media(head["id"], plan.media_ids)
        await create_scheduler_job(...)
        results[network] = {"status": "created", "mode": plan.mode, "post_id": head["id"], "warnings": plan.warnings}

Se o agendamento falhar, desfazer somente o post daquela rede. Depois de vínculo bem-sucedido, marcar os ativos como não temporários.

- [ ] **Step 4: Validar**

Run: pytest tests/api/test_posts.py tests/api/test_posts_network_routing.py tests/api/test_posts_media_drafts.py tests/api/test_profile_scope_posts.py -q
Expected: PASS com group_id, ordem e rollback por rede corretos.

- [ ] **Step 5: Commit**

    git add api/routers/posts.py frontend/src/api/posts.ts tests/api/test_posts_media_drafts.py tests/api/test_posts_network_routing.py
    git commit -m "feat: cria posts multi-rede por composição"

## Task 4: Fotos e carrosséis Meta

**Files:**
- Modify: apis/facebook.py
- Modify: apis/instagram.py
- Modify: scheduler/bot_post.py
- Modify: scheduler/bot_post_facebook.py
- Modify: scheduler/bot_post_instagram.py
- Test: tests/scheduler/test_bot_post_facebook.py
- Test: tests/scheduler/test_bot_post_instagram.py
- Test: tests/scheduler/test_scheduler_publish_flow.py

**Interfaces:**
- Consumes: post com mídias ordenadas anexadas ao plano da rede.
- Produces: uma publicação de foto, carrossel ou texto-only e atividade com o modo efetivo.

- [ ] **Step 1: Escrever testes de carrossel por ordem**

    def test_facebook_carousel_uploads_every_selected_image_in_order(monkeypatch):
        root = {"text": "copy", "medias": [image("a.jpg"), image("b.jpg")]}
        patch_common(monkeypatch, root)
        module.bot_post_facebook("job-carousel")
        assert uploaded_names == ["a.jpg", "b.jpg"]
        assert published_attached_media == ["fb-a", "fb-b"]

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/scheduler/test_bot_post_facebook.py tests/scheduler/test_bot_post_instagram.py -q
Expected: FAIL porque ambos escolhem apenas first_image.

- [ ] **Step 3: Implementar chamadas oficiais**

    def post_photos_as_page(page_token, page_id, image_urls, caption):
        uploaded = [upload_unpublished_photo(page_token, page_id, url) for url in image_urls]
        return publish_feed(page_token, page_id, caption, uploaded)

    def post_carousel(user_token, ig_user_id, children, caption):
        parent = create_container(ig_user_id, user_token, media_type="CAROUSEL", children=children, caption=caption)
        return publish_media_container(ig_user_id, user_token, parent)

Usar URL temporária Cloudinary e destruir cada recurso em finally. Não implementar vídeo neste task; modo não suportado retorna falha normalizada.

- [ ] **Step 4: Validar**

Run: pytest tests/scheduler/test_bot_post_facebook.py tests/scheduler/test_bot_post_instagram.py tests/scheduler/test_scheduler_publish_flow.py -q
Expected: PASS para texto, foto, carrossel, erro externo e escopo de perfil.

- [ ] **Step 5: Commit**

    git add apis/facebook.py apis/instagram.py scheduler/bot_post.py scheduler/bot_post_facebook.py scheduler/bot_post_instagram.py tests/scheduler/test_bot_post_facebook.py tests/scheduler/test_bot_post_instagram.py tests/scheduler/test_scheduler_publish_flow.py
    git commit -m "feat: publica imagens e carrosséis por rede"

## Task 5: X com upload de imagem e reconexão de escopo

**Files:**
- Modify: api/x_oauth.py
- Modify: apis/x.py
- Modify: scheduler/bot_post_x.py
- Modify: api/routers/credentials.py
- Test: tests/api/test_x_oauth.py
- Test: tests/scheduler/test_bot_post_x.py

**Interfaces:**
- Consumes: token OAuth do usuário com tweet.write, offline.access e media.write, além de imagens selecionadas.
- Produces: mídia enviada a POST /2/media/upload e post criado com os IDs retornados.

- [ ] **Step 1: Escrever testes de scope e anexos**

    def test_x_authorization_requests_media_write():
        assert "media.write" in unquote(get_user_auth_url("client", "challenge", "state"))

    def test_x_post_with_images_sends_media_ids(monkeypatch):
        XAPI.post_with_media("token", "copy", ["a.jpg", "b.jpg"])
        assert create_payload["media"]["media_ids"] == ["m-a", "m-b"]

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/api/test_x_oauth.py tests/scheduler/test_bot_post_x.py -q
Expected: FAIL porque scope e uploader ainda não existem.

- [ ] **Step 3: Implementar somente imagem**

    DEFAULT_SCOPES = "tweet.read tweet.write users.read offline.access media.write"

    def upload_media(access_token, file_path):
        with open(file_path, "rb") as source:
            response = requests.post(
                "https://api.x.com/2/media/upload",
                headers={"Authorization": f"Bearer {access_token}"},
                files={"media": source},
                data={"media_category": "tweet_image"},
                timeout=30,
            )
        return response.json()["data"]["id"]

Token conectado antes de media.write deve pedir Reconectar X. GIF e vídeo permanecem fora deste task.

- [ ] **Step 4: Validar**

Run: pytest tests/api/test_x_oauth.py tests/scheduler/test_bot_post_x.py -q
Expected: PASS para refresh, escopo, até quatro imagens e erro sanitizado.

- [ ] **Step 5: Commit**

    git add api/x_oauth.py apis/x.py scheduler/bot_post_x.py api/routers/credentials.py tests/api/test_x_oauth.py tests/scheduler/test_bot_post_x.py
    git commit -m "feat: publica imagens no X por oauth"

## Task 6: TikTok Photo Direct Post com Creator Info

**Files:**
- Modify: apis/tiktok.py
- Modify: scheduler/bot_post_tiktok.py
- Modify: api/routers/posts.py
- Modify: frontend/src/api/posts.ts
- Modify: frontend/src/pages/PostsPage.tsx
- Test: tests/api/test_media_composition.py
- Test: tests/scheduler/test_bot_post_tiktok.py

**Interfaces:**
- Consumes: até 35 URLs públicas verificadas, Creator Info e confirmação explícita do usuário.
- Produces: Photo Direct Post ou bloqueio legível, sem publicar.

- [ ] **Step 1: Escrever testes de Creator Info e limite**

    def test_tiktok_photo_plan_requires_creator_info_confirmation(client):
        response = client.post("/posts/preview-composition", json=tiktok_photo_payload())
        assert response.json()["plans"][0]["requires_creator_info"] is True

    def test_tiktok_photo_rejects_36_images():
        assert plan_network_composition("tiktok", ["copy"], images(36), 0).mode == "blocked"

- [ ] **Step 2: Confirmar falha**

Run: pytest tests/api/test_media_composition.py tests/scheduler/test_bot_post_tiktok.py -q
Expected: FAIL porque foto e Creator Info não existem.

- [ ] **Step 3: Implementar foto, não vídeo**

    def query_creator_info(access_token):
        return post("/v2/post/publish/creator_info/query/", access_token, {})

    def post_photos(access_token, image_urls, description, creator_info):
        return post("/v2/post/publish/content/init/", access_token, {
            "media_type": "PHOTO",
            "post_mode": "DIRECT_POST",
            "post_info": {"description": description, "privacy_level": creator_info["privacy_level"]},
            "source_info": {"source": "PULL_FROM_URL", "photo_images": image_urls, "photo_cover_index": 0},
        })

Preview devolve apenas as opções retornadas pelo token do perfil certo e exige confirmação. URLs precisam estar no domínio ou prefixo verificado do app.

- [ ] **Step 4: Validar**

Run: pytest tests/api/test_media_composition.py tests/scheduler/test_bot_post_tiktok.py -q
Expected: PASS para foto, carrossel de fotos, 35 e 36 itens, refresh e falhas sanitizadas.

- [ ] **Step 5: Commit**

    git add apis/tiktok.py scheduler/bot_post_tiktok.py api/routers/posts.py frontend/src/api/posts.ts frontend/src/pages/PostsPage.tsx tests/api/test_media_composition.py tests/scheduler/test_bot_post_tiktok.py
    git commit -m "feat: adiciona fotos do tiktok por composição"

## Task 7: Interface de composição, abas e confirmação

**Files:**
- Create: frontend/src/components/posts/MediaVariantTabs.tsx
- Modify: frontend/src/pages/PostsPage.tsx
- Modify: frontend/src/api/posts.ts
- Modify: frontend/src/lib/mediaComposition.ts

**Interfaces:**
- Consumes: MediaPlan do preview e metadados locais.
- Produces: seleção por grupo de redes, alertas claros e payload batch confirmado.

- [ ] **Step 1: Criar a apresentação pura de abas**

    export function MediaVariantTabs({ plans, onChange }: Props) {
      const groups = groupPlansByComposition(plans)
      return groups.length > 1 ? <SegmentedToggle options={groups.map(toOption)} onChange={onChange} /> : null
    }

Cada grupo mostra redes, modo final, arquivos e motivo. Reusar componentes e tokens existentes.

- [ ] **Step 2: Conectar upload, preview e confirmação**

    const media = await Promise.all(files.map((file) => postsApi.uploadDraftMedia(file)))
    const preview = await postsApi.previewComposition({ networks, texts_by_network, media_ids: media.map(({ id }) => id), product_ids })
    await postsApi.createBatch(confirmablePayload(preview.plans))

O modal lista cada rede como com mídia, somente texto ou não será enviada. Ação final continua única e devolve resultado por rede.

- [ ] **Step 3: Compilar**

Run: npm run build
Expected: PASS sem erro TypeScript; alerta preexistente de tamanho de bundle pode permanecer.

- [ ] **Step 4: Validar visualmente**

Run: Playwright no servidor local em 1440x900 e 390x844.
Expected: abas só aparecem quando há diferença, alertas não se sobrepõem e rede bloqueada não desabilita as compatíveis.

- [ ] **Step 5: Commit**

    git add frontend/src/components/posts/MediaVariantTabs.tsx frontend/src/pages/PostsPage.tsx frontend/src/api/posts.ts frontend/src/lib/mediaComposition.ts
    git commit -m "feat: mostra composição de mídia por rede"

## Task 8: Regressão, documentação e staging

**Files:**
- Modify: docs/MEMORY.md
- Modify: docs/PRD.md
- Modify: docs/TASK.md
- Modify: docs/ARCHITECTURE.md
- Modify: Projetos/ShopeeAutoVendas/00-INDICE-Estado-Atual.md no Vault
- Modify: Projetos/ShopeeAutoVendas/31-Contrato-OAuth-e-Publicacao.md no Vault

**Interfaces:**
- Consumes: testes, build e publicações de staging autorizadas.
- Produces: documentação baseada em evidência, nunca alegação antecipada.

- [ ] **Step 1: Regressão e sintaxe**

    python -m pytest tests/api/test_network_limits.py tests/api/test_media_composition.py tests/api/test_posts.py tests/api/test_posts_media_drafts.py tests/api/test_profile_scope_posts.py tests/scheduler/test_bot_post_x.py tests/scheduler/test_bot_post_facebook.py tests/scheduler/test_bot_post_instagram.py tests/scheduler/test_bot_post_tiktok.py -q
    python -m py_compile api/media_composition.py api/network_limits.py api/routers/posts.py apis/x.py apis/facebook.py apis/instagram.py apis/tiktok.py scheduler/bot_post_x.py scheduler/bot_post_facebook.py scheduler/bot_post_instagram.py scheduler/bot_post_tiktok.py

Expected: todos passam e nenhuma sintaxe falha.

- [ ] **Step 2: Validar staging por rede**

Publicar imagem simples e carrossel permitido em Threads, Facebook e Instagram; publicar imagem em X só após reconexão com media.write; publicar fotos no TikTok só após Creator Info e verificação de URL. Confirmar na conta alvo. Crédito, permissão ou auditoria externa são bloqueios, nunca sucesso.

- [ ] **Step 3: Atualizar docs e Drive**

Adicionar data, rede, modo e resultado observado sem credenciais. Copiar os documentos alterados para G:\Meu Drive\Backups-Projetos\ShopeeAutoVendas e comparar hashes.

- [ ] **Step 4: Revisar mudanças**

    git diff --check
    git status --short

Expected: nenhum whitespace inválido e somente arquivos deste escopo.

- [ ] **Step 5: Commit e staging**

    git add docs database api apis scheduler frontend tests
    git commit -m "docs: registra composição de mídia por rede"
    git push origin staging

Não fazer merge para main até o usuário validar staging explicitamente.

## Self-review do plano

- Cobertura do spec: Tasks 1-3 cobrem planner, fallback, isolamento e dados; Tasks 4-6 cobrem publicadores; Task 7 cobre interface; Task 8 cobre validação e documentação.
- Placeholders: não há marcadores pendentes nem passo sem arquivo, contrato, comando ou critério de sucesso.
- Consistência: MediaPlan, media_ids, text_only, blocked_reason, user_id e profile_id usam os mesmos nomes em todas as tarefas.
- Review Focus: cada risco possui teste nas Tasks 1, 2, 3, 5/6 e 8, respectivamente.
