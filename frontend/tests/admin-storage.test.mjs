import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('ADMIN usa painel existente, mostra buckets e limiares sem inventar egress', () => {
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
  const data = {
    counts: null, scale: null,
    render: { cpu: null, cpu_limit: null, memory: null, memory_limit: null },
    storage: { status: 'available', collected_at: new Date().toISOString(),
      used_bytes: 900 * 1048576, reserved_bytes: 0, quota_bytes: 1024 * 1048576,
      warning_percent: 75, critical_percent: 85, block_percent: 90,
      buckets: [{ bucket: 'post-media', objects: 3, used_bytes: 900 * 1048576 }] },
  }
  const html = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(html.includes('Storage · arquivos e cota Free'))
  assert.ok(html.includes('post-media'))
  assert.ok(html.includes('nível crítico'))
  assert.ok(html.includes('Consultar a transferência oficial'))
  assert.ok(!html.includes('cota acumulada por usuário'))
  data.storage.used_bytes = 462177
  const tiny = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(tiny.includes('<0,1%'), 'ocupacao real nao pode aparecer como zero')
  data.storage = { status: 'unavailable' }
  const unavailable = JSON.stringify(exports.ScaleMetrics({ data }))
  assert.ok(unavailable.includes('Consumo indisponível'))
  assert.ok(unavailable.includes('novos uploads são recusados'))
})
