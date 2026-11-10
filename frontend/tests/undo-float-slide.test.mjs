import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')

test('Posts, Produtos e Listas excluem com Desfazer (exclusão adiada, item some na hora)', () => {
  for (const [file, kind, api] of [['pages/PostsPage.tsx', 'posts', 'postsApi'], ['pages/ProductsPage.tsx', 'products', 'productsApi'], ['pages/ListasPage.tsx', 'lists', 'listsApi']]) {
    const s = src(file)
    assert.match(s, /scheduleUndoableDelete\(/, file)
    assert.match(s, new RegExp(`kind: "${kind}"`), file)
    assert.match(s, new RegExp(`useHiddenIds\\("${kind}"\\)`), file)
    assert.match(s, new RegExp(`${api}\\.delete\\(id, keepalive\\)`), file)
  }
})

test('exclusão pendente é enviada ao fechar a aba (pagehide) e Desfazer cancela o envio', () => {
  const s = src('lib/undoableDelete.ts')
  assert.match(s, /addEventListener\('pagehide'/)
  assert.match(s, /export function undoDelete/)
  assert.match(s, /clearTimeout\(p\.timer\)/)
  assert.match(src('lib/api.ts'), /keepalive: true/)
})

test('aviso com ação não é agrupado em ×N (cada exclusão mantém seu Desfazer)', () => {
  assert.match(src('stores/toastStore.ts'), /!toast\.action/)
  assert.match(src('components/ui/Toaster.tsx'), /toast-action/)
})

test('rótulo flutuante em TextInput e Textarea, respeitando movimento reduzido', () => {
  for (const f of ['components/ui/TextInput.tsx', 'components/ui/Textarea.tsx']) assert.match(src(f), /ao-float-label/, f)
  const css = src('components/ui/motion.css')
  assert.match(css, /:placeholder-shown\) ~ \.ao-float-label/)
  assert.match(css, /:-webkit-autofill ~ \.ao-float-label/)
  assert.match(css, /prefers-reduced-motion: reduce\) \{ \.ao-float-label/)
})

test('ativar campanha usa deslizar para confirmar, com alternativa de teclado', () => {
  const planner = src('components/campaigns/CampaignPlanner.tsx')
  assert.match(planner, /<SlideToConfirm/)
  assert.doesNotMatch(planner, /<Button variant="primary" icon="send"\s+disabled=\{Boolean\(activationBlockReason\)/)
  const s = src('components/ui/SlideToConfirm.tsx')
  assert.match(s, /SLIDE_CONFIRM_THRESHOLD = 0\.92/)
  assert.match(s, /event\.key !== "Enter" && event\.key !== " "/)
  assert.match(s, /event\.detail === 0/)
})

test('cabeçalho do dashboard é digitado uma vez por login, com texto completo para leitor de tela', () => {
  const m = src('lib/motion.ts')
  assert.match(m, /export function useTypewriter/)
  assert.match(m, /prefersReducedMotion\(\) \|\| alreadyCounted\(label\)/)
  const d = src('pages/DashboardPage.tsx')
  assert.match(d, /useTypewriter\(subtitle, 'dashboard-subtitulo'\)/)
  assert.match(d, /csp-named-sr-only">\{subtitle\}/)
})
