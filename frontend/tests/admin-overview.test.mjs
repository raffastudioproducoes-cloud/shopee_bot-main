import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('métricas ausentes não viram zero nem gráficos fictícios', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/pages/AdminOverviewPage.tsx', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const exports = {}
  let result = { data: { counts: null, daily: [], supabase: { status: 'unavailable' }, render: { status: 'not_configured', cpu: null, memory: null }, unavailable: { paying_accounts: 'Sem cobrança', traffic_sources: 'Sem origem', session_time: 'Sem tempo', location: 'Sem localização' }, notes: [], updated_at: '2026-10-15T00:00:00Z' } }
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useState: value => [value, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-query') return { useQuery: () => result }
    return new Proxy({}, { get: (_, key) => key })
  } })
  const tree = JSON.stringify(exports.default())
  assert.ok(tree.includes('Indisponível'))
  assert.ok(tree.includes('Sem localização'))
  assert.ok(!tree.includes('MetricTrend'))
  assert.ok(!tree.includes('PlanRings'))
  result = { error: new Error('private diagnostic') }
  const errorTree = JSON.stringify(exports.default())
  assert.ok(errorTree.includes('alert'))
  assert.ok(!errorTree.includes('private diagnostic'))
  result = { isLoading: true }
  assert.ok(JSON.stringify(exports.default()).includes('PageSkeleton'))
})
