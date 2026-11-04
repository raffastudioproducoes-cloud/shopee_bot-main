import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const src = (path) => readFile(new URL('../src/' + path, import.meta.url), 'utf8')

test('dashboard usa resumo de conta e renderiza recentes reais, sem links entre perfis', async () => {
  const [page, api] = await Promise.all([src('pages/DashboardPage.tsx'), src('api/dashboard.ts')])
  assert.match(api, /api\.get<DashboardStats>\('\/dashboard\/stats'\)/)
  for (const field of ['products_count', 'posts_count', 'lists_count', 'scheduled_posts', 'recent_posts', 'recent_activities']) {
    assert.ok(api.includes(field), 'campo de contrato: ' + field)
  }
  assert.match(page, /stats\.recent_posts\.map/)
  assert.match(page, /stats\.recent_activities\.map/)
  assert.match(page, /post\.text_preview/)
  assert.match(page, /activity\.label/)
  assert.match(page, /todos os perfis/)
  assert.doesNotMatch(page, /postsApi|getPost|activateProfile|dangerouslySetInnerHTML|href=/)
})

test('vazio só vem de array confirmado; falha não vira zero ou nenhum registro', async () => {
  const page = await src('pages/DashboardPage.tsx')
  assert.match(page, /if \(error \|\| !stats\)/)
  assert.match(page, /role="alert"/)
  assert.match(page, /Tentar novamente/)
  assert.match(page, /!Array\.isArray\(stats\.recent_posts\)/)
  assert.match(page, /stats\.recent_posts\.length === 0/)
  assert.match(page, /!Array\.isArray\(stats\.recent_activities\)/)
  assert.match(page, /stats\.recent_activities\.length === 0/)
  assert.doesNotMatch(page, /\?\? 0/)
  assert.match(page, /Number\.isFinite\(value\)/)
})

test('cache é exclusivo por conta e só consulta sessão confirmada', async () => {
  const hook = await src('hooks/useDashboard.ts')
  assert.match(hook, /queryKey: \['dashboard', accountId\]/)
  assert.match(hook, /enabled: Boolean\(accountId && verified\)/)
  assert.match(hook, /gcTime: 0/)
  assert.match(hook, /staleTime: 0/)
  assert.match(hook, /refetchOnMount: 'always'/)
  assert.match(hook, /refetchOnWindowFocus: 'always'/)
  assert.doesNotMatch(hook, /placeholderData|keepPreviousData|profileId/)
})

test('retornar de uma mutação em outra página exige leitura nova, sem cache anterior', async () => {
  // Dashboard é uma página exclusiva do Outlet: criação/edição ficam em outras
  // rotas. Não alterar o MutationCache global para um resumo desmontado.
  const hook = await src('hooks/useDashboard.ts')
  assert.match(hook, /gcTime: 0/)
  assert.match(hook, /staleTime: 0/)
  assert.match(hook, /refetchOnMount: 'always'/)
})

test('ações rápidas apontam para criação e router aceita só intenção reconhecida', async () => {
  const [page, routes, search] = await Promise.all([src('pages/DashboardPage.tsx'), src('router.tsx'), src('lib/creationIntent.ts')])
  assert.match(page, /to: '\/posts\/criar'/)
  assert.match(page, /to: '\/products', search: \{ action: 'create' \}/)
  assert.match(page, /to: '\/lists', search: \{ action: 'create' \}/)
  assert.equal((routes.match(/validateSearch: creationSearch/g) ?? []).length, 2)
  assert.match(search, /search\.action === 'create' \? \{ action: 'create' \} : \{\}/)
})

test('intenção aguarda plano e reutiliza modais, sem contornar cotas', async () => {
  const [products, lists] = await Promise.all([src('pages/ProductsPage.tsx'), src('pages/ListasPage.tsx')])
  for (const page of [products, lists]) {
    assert.match(page, /action !== "create" \|\| planQuery\.isPending \|\| planQuery\.isError \|\| !planQuery\.data/)
    assert.match(page, /search: \{\}, replace: true/)
  }
  assert.match(products, /if \(!productsAtLimit\) openCreateModal\(\)/)
  assert.match(products, /const openCreateModal = useCallback\(\(\) => \{\s*if \(productsAtLimit\) return/)
  assert.match(lists, /if \(!listsAtLimit\) \{\s*setEditingList\(null\)\s*setModalOpen\(true\)/)
  assert.match(lists, /else if \(!listsAtLimit\) \{\s*createMutation\.mutate/)
})

test('dashboard preserva leitura mobile e semântica de listas/datas', async () => {
  const page = await src('pages/DashboardPage.tsx')
  assert.match(page, /minmax\(min\(100%, 200px\), 1fr\)/)
  assert.match(page, /overflowWrap: 'anywhere'/)
  assert.match(page, /<ul aria-label="Postagens recentes/)
  assert.match(page, /<ul aria-label="Atividades recentes/)
  assert.match(page, /<time dateTime=\{value\}/)
  assert.match(page, /timeZone: 'America\/Sao_Paulo'/)
  assert.match(page, /Number\.isNaN\(Date\.parse\(value\)\)/)
})
