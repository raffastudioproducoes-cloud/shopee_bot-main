import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

// Transpila em memória: o CI roda Node 20, sem suporte nativo a .ts.
const source = readFileSync(new URL('../src/lib/postMetrics.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
})
const pm = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('métrica indisponível vira traço, zero continua zero', () => {
  assert.equal(pm.formatMetric(null), '—')
  assert.equal(pm.formatMetric(undefined), '—')
  assert.equal(pm.formatMetric(0), '0')
  assert.equal(pm.formatMetric(1234), (1234).toLocaleString('pt-BR'))
  assert.equal(pm.UNAVAILABLE_TOOLTIP, 'a rede não fornece esta métrica')
})

test('ordenação deixa nulos no fim nos dois sentidos e desempata pela data', () => {
  const rows = [
    { job_id: 'a', views: null, finished_at: '2026-11-10' },
    { job_id: 'b', views: 5, finished_at: '2026-11-09' },
    { job_id: 'c', views: 9, finished_at: '2026-11-08' },
    { job_id: 'd', views: 5, finished_at: '2026-11-11' },
  ]
  assert.deepEqual(pm.sortByMetric(rows, 'views').map((r) => r.job_id), ['c', 'd', 'b', 'a'])
  assert.deepEqual(pm.sortByMetric(rows, 'views', false).map((r) => r.job_id), ['d', 'b', 'c', 'a'])
})

test('período personalizado aceita até 365 dias e recusa fim antes do início', () => {
  assert.equal(pm.rangeDays('2026-01-01', '2026-12-31'), 365)
  assert.equal(pm.customRangeError('2026-01-01', '2026-12-31'), null)
  assert.match(pm.customRangeError('2025-01-01', '2026-01-01'), /365 dias/)
  assert.match(pm.customRangeError('2026-02-01', '2026-01-01'), /posterior/)
  assert.match(pm.customRangeError('', '2026-01-01'), /início e fim/)
})

test('query do período inclui fuso e só aceita opções conhecidas', () => {
  assert.equal(pm.periodQuery('90', '', '', 'Europe/Lisbon'), 'days=90&tz=Europe%2FLisbon')
  assert.equal(pm.periodQuery('365', '', '', 'UTC'), 'days=365&tz=UTC')
  assert.equal(pm.periodQuery('custom', '2026-01-01', '2026-01-31', 'UTC'), 'from=2026-01-01&to=2026-01-31&tz=UTC')
  assert.equal(pm.periodQuery('custom', '2026-02-01', '2026-01-31', 'UTC'), null)
  assert.equal(pm.periodQuery('999', '', '', 'UTC'), null)
  assert.deepEqual([...pm.PERIOD_OPTIONS], ['7', '30', '90', '180', '365', 'custom'])
})

test('evolução soma redes por dia sem transformar ausência em zero', () => {
  const totals = pm.seriesTotals([
    { day: '2026-11-02', network: 'threads', views: 4 },
    { day: '2026-11-01', network: 'threads', views: null },
    { day: '2026-11-02', network: 'x', views: 6 },
  ], 'views')
  assert.deepEqual(totals, [{ day: '2026-11-01', value: null }, { day: '2026-11-02', value: 10 }])
})

test('telas usam o helper: traço com tooltip, fuso do usuário e card no Dashboard', () => {
  const panel = readFileSync(new URL('../src/components/PostMetricsPanel.tsx', import.meta.url), 'utf8')
  const page = readFileSync(new URL('../src/pages/AnalyticsPage.tsx', import.meta.url), 'utf8')
  const dash = readFileSync(new URL('../src/pages/DashboardPage.tsx', import.meta.url), 'utf8')
  const card = readFileSync(new URL('../src/components/DashboardBestPost.tsx', import.meta.url), 'utf8')
  assert.match(panel, /title=\{UNAVAILABLE_TOOLTIP\}/)
  assert.match(panel, /formatInstant\(/)
  assert.match(panel, /\/analytics\/ranking\?/)
  assert.match(page, /periodQuery\(days, customFrom, customTo, getUserTimeZone\(\)\)/)
  assert.match(page, /value: 'custom', label: 'Personalizado'/)
  assert.match(dash, /<DashboardBestPost userId=\{userId\} \/>/)
  assert.match(card, /days=30&metric=views/)
  assert.match(card, /to: '\/analytics'/)
})
