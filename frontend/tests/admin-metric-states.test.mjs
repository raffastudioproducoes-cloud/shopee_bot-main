import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('falha de atualização mantém última coleta, avisa idade e permite tentar novamente', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/pages/AdminOverviewPage.tsx', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const exports = {}
  let refreshed = 0
  let compare = false
  class Denied extends Error { constructor() { super('private access failure'); this.status = 403 } }
  let result = { error: Error('private failure'), refetch: () => refreshed++, data: {
    counts: null, daily: [], supabase: { status: 'unavailable' }, render: { status: 'not_configured' },
    notes: [], unavailable: {}, updated_at: '2000-01-01T00:00:00Z', status: 'partial',
  } }
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useState: value => [typeof value === 'boolean' ? compare : value, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-query') return { useQuery: () => result }
    if (name === '../lib/api') return { ApiError: Denied }
    if (name.includes('metricsPresentation')) return { isStale: () => true, formatMetricTime: () => '01/01/2000', comparisonDelta: () => 'Sem base percentual' }
    return new Proxy({}, { get: (_, key) => key })
  } })
  const nodes = node => Array.isArray(node) ? node.flatMap(nodes) : node && typeof node === 'object' ? [node, ...nodes(node.props?.children)] : []
  let tree = exports.default()
  assert.ok(JSON.stringify(tree).includes('Última coleta'))
  assert.ok(JSON.stringify(tree).includes('Dados antigos'))
  assert.ok(!JSON.stringify(tree).includes('private failure'))
  nodes(tree).find(node => node.props?.children === 'Atualizar agora').props.onClick()
  assert.equal(refreshed, 1)
  compare = true
  assert.ok(JSON.stringify(exports.default()).includes('Comparação indisponível'))
  result = { ...result, error: new Denied() }
  assert.ok(!JSON.stringify(exports.default()).includes('Contas atuais'), 'acesso revogado não deve preservar a exibição dos dados')
  result = { error: Error('private failure'), refetch: () => refreshed++ }
  tree = exports.default()
  assert.ok(JSON.stringify(tree).includes('Tentar novamente'))
})
