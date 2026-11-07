import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

// O CI utiliza Node 20, que não suporta importação direta de arquivos .ts.
// Transpilamos o módulo puro em memória sem alterar seu contrato de produção.
const paginationSource = readFileSync(new URL('../src/lib/postHistoryPagination.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(paginationSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
})
const { POSTS_PER_PAGE, POSTS_FETCH_LIMIT, paginatePostHistory, canAdvancePostHistory } =
  await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

const posts = Array.from({ length: 37 }, (_, index) => ({ id: 37 - index }))

test('página de histórico mostra no máximo 15 posts, mantendo a ordem recebida', () => {
  assert.equal(POSTS_PER_PAGE, 15)
  assert.equal(POSTS_FETCH_LIMIT % POSTS_PER_PAGE, 0)
  assert.deepEqual(paginatePostHistory(posts, 1).items.map((p) => p.id), posts.slice(0, 15).map((p) => p.id))
  assert.deepEqual(paginatePostHistory(posts, 2).items.map((p) => p.id), posts.slice(15, 30).map((p) => p.id))
  assert.deepEqual(paginatePostHistory(posts, 3).items.map((p) => p.id), posts.slice(30).map((p) => p.id))
  assert.equal(paginatePostHistory(posts, 3).items.length, 7)
})

test('paginação faz clamp e não cria página vazia após exclusão ou refiltro', () => {
  assert.equal(paginatePostHistory(posts, 0).page, 1)
  assert.equal(paginatePostHistory(posts, -4).page, 1)
  assert.equal(paginatePostHistory(posts, 900).page, 3)
  assert.equal(paginatePostHistory(posts, Number.NaN).page, 1)
  assert.deepEqual(paginatePostHistory([], 9), { page: 1, loadedPages: 1, items: [] })
})

test('filtros de busca são paginados depois de aplicados', () => {
  const filtered = posts.filter((post) => post.id % 2 === 0)
  const p1 = paginatePostHistory(filtered, 1)
  const p2 = paginatePostHistory(filtered, 2)
  assert.equal(p1.items.length, 15)
  assert.equal(p2.items.length, 3)
  assert.ok(p1.items.every((item) => item.id % 2 === 0))
  assert.ok(p2.items.every((item) => item.id % 2 === 0))
})

test('próxima página em cache funciona e cursor remoto só sem busca ativa', () => {
  assert.equal(canAdvancePostHistory(1, 3, false, false), true)
  assert.equal(canAdvancePostHistory(3, 3, true, false), true)
  assert.equal(canAdvancePostHistory(3, 3, false, false), false)
  assert.equal(canAdvancePostHistory(3, 3, true, true), false)
  assert.equal(canAdvancePostHistory(1, 3, true, true), true)
})

test('lista parcial com até 15 posts não apresenta páginas extras', () => {
  assert.equal(paginatePostHistory(posts.slice(0, 15), 1).loadedPages, 1)
  assert.equal(paginatePostHistory(posts.slice(0, 16), 1).loadedPages, 2)
})

test('PostsPage usa a busca contextual existente antes de paginar, com navegação acessível', () => {
  const page = readFileSync(new URL('../src/pages/PostsPage.tsx', import.meta.url), 'utf8')
  assert.ok(page.indexOf('matchesPost(post, searchQuery)') < page.indexOf('paginatePostHistory(visiblePosts, historyPage)'))
  assert.match(page, /const visiblePosts = hasActiveSearch \? posts\.filter\(\(post\) => matchesPost\(post, searchQuery\)\)/)
  assert.match(page, /\{pagination\.items\.map\(\(post, index\) => \(/)
  assert.match(page, /aria-label="Paginação do histórico de posts"/)
  assert.match(page, /aria-label="Página anterior"/)
  assert.match(page, /aria-label="Próxima página"/)
  assert.match(page, /setHistoryPage\(1\), \[searchQuery, activeProfileId\]/)
  assert.match(page, /fetchNextPage\(\)\.then\(/)
  assert.doesNotMatch(page, /Carregar mais posts/)
})
