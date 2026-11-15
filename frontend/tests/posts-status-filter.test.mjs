import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

// Node 20 do CI não importa .ts: transpila e executa num contexto isolado.
const transpiled = ts.transpileModule(
  readFileSync(new URL('../src/lib/postStatusFilter.ts', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText
const mod = { exports: {} }
vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
const { STATUS_FILTERS, countPostsByStatus, matchesStatusFilter, parseStatusFilter, postStatusGroup } = mod.exports

const post = (status) => ({ last_result: status === undefined ? null : { status } })
const page = readFileSync(new URL('../src/pages/PostsPage.tsx', import.meta.url), 'utf8')
const modals = readFileSync(new URL('../src/components/posts/PublicationDecisionModals.tsx', import.meta.url), 'utf8')
const router = readFileSync(new URL('../src/router.tsx', import.meta.url), 'utf8')
const backend = readFileSync(new URL('../../api/routers/posts.py', import.meta.url), 'utf8')

test('cada status real da API cai num grupo do filtro', () => {
  assert.equal(postStatusGroup(post('published')), 'published')
  assert.equal(postStatusGroup(post('manual_confirmed')), 'manual')
  assert.equal(postStatusGroup(post('reported_removed')), 'manual')
  assert.equal(postStatusGroup(post('failed')), 'failed')
  assert.equal(postStatusGroup(post('unknown')), 'unknown')
  assert.equal(postStatusGroup(post('running')), 'running')
  assert.equal(postStatusGroup(post('retry_pending')), 'running')
  assert.equal(postStatusGroup(post(undefined)), 'pending')
  assert.equal(postStatusGroup(post(null)), 'pending')
})

test('"Precisam de atenção" junta erro e sem confirmação, e só eles', () => {
  assert.ok(matchesStatusFilter(post('failed'), 'attention'))
  assert.ok(matchesStatusFilter(post('unknown'), 'attention'))
  for (const status of ['published', 'manual_confirmed', 'running', undefined]) {
    assert.ok(!matchesStatusFilter(post(status), 'attention'), String(status))
  }
  assert.ok(matchesStatusFilter(post('failed'), 'all'))
})

test('contadores por filtro', () => {
  const counts = countPostsByStatus([post('failed'), post('unknown'), post('unknown'), post('published'), post(undefined)])
  assert.equal(counts.all, 5)
  assert.equal(counts.attention, 3)
  assert.equal(counts.unknown, 2)
  assert.equal(counts.failed, 1)
  assert.equal(counts.published, 1)
  assert.equal(counts.pending, 1)
  assert.equal(counts.manual, 0)
})

test('URL inválida volta para "Todos" (nada de filtro inventado)', () => {
  assert.equal(parseStatusFilter('attention'), 'attention')
  assert.equal(parseStatusFilter('drop table'), 'all')
  assert.equal(parseStatusFilter(undefined), 'all')
  assert.deepEqual([...STATUS_FILTERS.map((f) => f.key)],
    ['all', 'attention', 'unknown', 'failed', 'running', 'pending', 'published', 'manual'])
})

test('os grupos do front são exatamente os aceitos pelo servidor', () => {
  const literal = backend.match(/PostStatusFilter = Literal\[([^\]]+)\]/)[1]
  const server = [...literal.matchAll(/"(\w+)"/g)].map((m) => m[1]).sort()
  const front = [...STATUS_FILTERS.map((f) => f.key).filter((k) => k !== 'all')].sort()
  assert.deepEqual(front, server)
})

test('filtro de status vai para o servidor e fica na URL', () => {
  assert.match(page, /postsApi\.list\(\{ cursor: pageParam, limit: POSTS_FETCH_LIMIT, status: statusFilter \}\)/)
  assert.match(page, /useSearch\(\{ strict: false \}\)/)
  assert.match(page, /parseStatusFilter\(urlSearch\.status\)/)
  assert.match(router, /path: "\/posts",\n\s*\/\/[^\n]*\n\s*validateSearch/)
  assert.match(page, /EMPTY_STATUS_MESSAGE\[statusFilter\]/)
})

test('botão de conferência volta para todas as redes; reenvio só para falha', () => {
  // Antes só aparecia com post.network === "threads".
  assert.doesNotMatch(page, /status === "unknown" && post\.network === "threads"/)
  assert.match(page, /status === "unknown" && post\.publication_origin !== "campaign"/)
  assert.match(page, /status === "failed" && post\.last_result\.job_id/)
  assert.match(modals, /Confirmo que foi publicado/)
  assert.match(modals, /Não foi publicado/)
  assert.match(modals, /postsApi\.resolveUnknown/)
  assert.match(modals, /postsApi\.retryFailed/)
})
