import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')

test('a análise de redes fica embaixo do dashboard, carregada sob demanda e só quando visível', () => {
  const dash = src('pages/DashboardPage.tsx')
  assert.match(dash, /lazy\(\(\) => import\('\.\/AnalyticsPage'\)\)/)
  assert.match(dash, /<section id="analises" aria-label="Análise de redes"/)
  assert.match(dash, /<LazyWhenVisible[\s\S]*<AnalyticsSection embedded \/>/)
  const lazy = src('components/ui/LazyWhenVisible.tsx')
  assert.match(lazy, /IntersectionObserver/)
  assert.match(lazy, /observer\.disconnect\(\)/)
  assert.match(lazy, /typeof IntersectionObserver === "undefined"/, 'sem suporte, monta direto')
})

test('incorporada, a análise usa h2 (a página já tem um h1); sozinha continua h1', () => {
  const page = src('pages/AnalyticsPage.tsx')
  assert.match(page, /embedded\s*\?\s*<h2/s)
  assert.match(page, /<h1 className="csp-s-0169">Análise de redes<\/h1>/)
})

test('rota /analytics virou atalho para a seção do dashboard e o item sai do menu', () => {
  const router = src('router.tsx')
  assert.match(router, /path: "\/analytics"[\s\S]*redirect\(\{ to: "\/app", hash: "analises" \}\)/)
  assert.doesNotMatch(src('pages/PanelPage.tsx'), /label: 'Análises'/)
})

test('ADM entra pelo dashboard: sem desvio para /admin/overview no login, na raiz, em /app e no retorno das páginas legais', () => {
  for (const f of ['pages/LoginPage.tsx', 'pages/PanelPage.tsx', 'pages/legal/LegalLayout.tsx']) {
    assert.doesNotMatch(src(f), /navigate\(\{ to: [^)]*admin\/overview/, f)
  }
  const router = src('router.tsx')
  assert.doesNotMatch(router.match(/const landingRoute[\s\S]*?component: PresentationPage/)?.[0] ?? '', /admin\/overview/)
})
