import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('controle de escala distingue dados ausentes, snapshots antigos e avisos fundamentados', () => {
  const helpers = {}
  const compile = path => ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  runInNewContext(compile('../src/components/admin/metricsPresentation.ts'), { exports: helpers })
  const exports = {}
  const jsx = (type, props) => ({ type, props })
  runInNewContext(compile('../src/components/admin/ScaleMetrics.tsx'), { exports, require(name) {
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name.includes('metricsPresentation')) return helpers
    return new Proxy({}, { get: (_, key) => key })
  } })
  const data = { counts: null, render: { cpu: null, cpu_limit: null, memory: null, memory_limit: null } }
  let text = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(text.includes('Histórico ainda sem amostras'))
  assert.ok(text.includes('Indisponível'))
  const cpu = { value: 0.9, unit: 'cpu', timestamp: new Date().toISOString() }
  data.render = { ...data.render, cpu, cpu_limit: { ...cpu, value: 1 } }
  text = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(text.includes('CPU acima de 80%'))
  data.render.cpu = { ...cpu, timestamp: '2000-01-01T00:00:00Z' }
  text = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(!text.includes('CPU acima de 80%'), 'amostra antiga não gera alerta atual')
  data.scale = { database: { blocked_connections: 2, oldest_transaction_seconds: 120, tables: [] }, capacity_history: [], consumption: [] }
  text = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(text.includes('2 conexões bloqueadas'))
  assert.ok(text.includes('transação aberta há mais de um minuto'))
})
