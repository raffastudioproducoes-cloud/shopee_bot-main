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
  assert.match(routes, /component: CreatePostPage/)
  assert.ok(
    panel.indexOf("value: '/posts/criar'") > panel.indexOf("value: '/posts'") &&
    panel.indexOf("value: '/posts/criar'") < panel.indexOf("value: '/automacao-posts'"),
    "Criar POST fica no menu lateral logo antes de Automação",
  )
})

test("Edição privada mantém o ID original e não cria nem dispara outro post", async () => {
  const [routes, page, modal, api, backend] = await Promise.all([
    src("router.tsx"),
    src("pages/EditPostPage.tsx"),
    src("components/posts/PostDetailsModal.tsx"),
    src("api/posts.ts"),
    readFile(new URL("../../api/routers/posts.py", import.meta.url), "utf8"),
  ])
  assert.match(routes, /path: "\/posts\/\$postId\/editar"/)
  assert.match(routes, /component: EditPostPage/)
  assert.match(page, /postsApi\.get\(id\)/)
  assert.match(page, /postsApi\.update\(id,/)
  assert.doesNotMatch(page, /postsApi\.createBatch|postsApi\.publishNow/)
  assert.match(page, /post=\{post\}/)
  assert.match(modal, /canOfferEdit/)
  assert.match(modal, /\/posts\/\$postId\/editar/)
  assert.match(api, /async update\(id: number/)
  assert.match(backend, /_ensure_post_editable\(user_id, post_id, profile_id, post\)/)
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
