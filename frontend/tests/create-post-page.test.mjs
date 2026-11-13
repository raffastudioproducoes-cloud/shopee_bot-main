import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const src = (path) => readFile(new URL(`../src/${path}`, import.meta.url), "utf8")

test("Criar POST é uma rota privada dedicada, em cima de Automação", async () => {
  const [routes, panel] = await Promise.all([
    src("router.tsx"),
    src("pages/PanelPage.tsx"),
  ])
  assert.match(routes, /path: "\/posts\/criar"/)
  assert.match(routes, /component: (?:lazyRoute\()?CreatePostPage/)
  assert.ok(
    panel.indexOf("value: '/posts/criar'") > panel.indexOf("value: '/posts'") &&
    panel.indexOf("value: '/posts/criar'") < panel.indexOf("value: '/automacao-posts'"),
    "Criar POST fica no menu lateral logo antes de Automação",
  )
})

test("Posts mantém a lista e o modal de detalhes, sem formulário de criação", async () => {
  const page = await src("pages/PostsPage.tsx")
  assert.match(page, /post-list-id/)
  assert.match(page, /<PostDetailsModal/)
  assert.doesNotMatch(page, /<PostModal/)
  assert.doesNotMatch(page, /Novo post\s*<\/Button>/)
})

test("Compositor reutiliza as funções anteriores em página, com rascunho", async () => {
  const [page, composer] = await Promise.all([
    src("pages/CreatePostPage.tsx"),
    src("components/posts/PostComposer.tsx"),
  ])
  assert.match(page, /<PostComposer/)
  assert.match(composer, /post-composer-layout/)
  assert.match(composer, /formDraftKey/)
  assert.match(composer, /useAutosavedDraft/)
  assert.match(composer, /<PostProductPicker/)
  assert.match(composer, /<NetworkPicker/)
  assert.match(composer, /<PostTimePicker/)
  assert.match(composer, /<PostLivePreview/)
  assert.doesNotMatch(composer, /<Modal\b/)
})

test("foto da Shopee e arquivos de PC/celular coexistem no editor", async () => {
  const [composer, productsApi, create] = await Promise.all([
    src("components/posts/PostComposer.tsx"),
    src("api/products.ts"),
    src("pages/CreatePostPage.tsx"),
  ])
  assert.match(composer, /Usar fotos dos produtos Shopee na publicação/)
  assert.match(composer, /type="file"/)
  assert.match(composer, /multiple=\{!post\}/)
  assert.match(composer, /Mídia \(imagem\/vídeo\)/)
  assert.match(composer, /importablePhotos/)
  assert.match(productsApi, /\/products\/\$\{id\}\/image\/download/)
  assert.match(create, /postsApi\.importProductImageDraft/)
  assert.match(create, /postsApi\.uploadDraftMedia/)

})

test("mídias cadastradas em Produtos entram pré-selecionadas e podem ser desmarcadas", async () => {
  const [composer, postsApi, create] = await Promise.all([
    src("components/posts/PostComposer.tsx"),
    src("api/posts.ts"),
    src("pages/CreatePostPage.tsx"),
  ])
  // Galeria do produto carregada no composer; seleção guarda só as desmarcadas.
  assert.match(composer, /productsApi\.media\(/)
  assert.match(composer, /skippedProductMedia/)
  assert.match(composer, /Mídias cadastradas no produto/)
  // Entram na validação por rede (mesmo array `media` usado pelos limites).
  assert.match(composer, /\.\.\.chosenProductMedia\.map\(\(m\) => \(\{ name: m\.file_name/)
  // Cópia no servidor por ID, antes da foto principal Shopee (mesma ordem do array).
  assert.match(postsApi, /\/posts\/product-media-drafts\//)
  const order = create.indexOf("importProductMediaDraft")
  assert.ok(order > 0 && order < create.indexOf("importProductImageDraft"))
})


test("campanha salva snapshots no servidor sem acionar posts ou scheduler", async () => {
  const [planner, api] = await Promise.all([
    src("components/campaigns/CampaignPlanner.tsx"),
    src("api/campaigns.ts"),
  ])
  assert.match(planner, /Salvar rascunho/)
  assert.match(planner, /Continuar rascunho salvo/)
  assert.match(planner, /campaignsApi\.createDraft/)
  assert.match(planner, /campaignsApi\.updateDraft/)
  assert.match(planner, /campaignsApi\.getDraft/)
  assert.match(api, /\x27\/campaigns\/drafts\x27/)
  assert.doesNotMatch(planner, /postsApi\.create|schedulePost|publishPost/)
})

test("campanha gera copy pela IA existente e altera somente o snapshot do item", async () => {
  const [planner, snapshot] = await Promise.all([
    src("components/campaigns/CampaignPlanner.tsx"),
    src("lib/campaignSnapshots.ts"),
  ])
  assert.match(planner, /postsApi\.generateCopy\(id, persona, \[\], \{ descriptionOnly: true \}\)/)
  assert.match(planner, /patchCampaignSnapshot\(currentSnapshots, request\.id, \{ copy: result\.text \}\)/)
  assert.match(planner, /Usar descrição salva em Produtos/)
  assert.match(snapshot, /copy: product\.description\?\.trim\(\) \?\? ""/)
  assert.doesNotMatch(planner, /productsApi\.update/)
})
