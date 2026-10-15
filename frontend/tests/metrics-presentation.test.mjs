import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('idade, fuso e comparação distinguem ausência de base de queda real', () => {
  const exports = {}
  const code = ts.transpileModule(readFileSync(new URL('../src/components/admin/metricsPresentation.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  runInNewContext(code, { exports })
  const now = Date.parse('2026-10-15T06:00:00Z')
  assert.equal(exports.isStale('2026-10-15T05:59:00Z', 300000, now), false)
  assert.equal(exports.isStale('2026-10-15T05:50:00Z', 300000, now), true)
  assert.equal(exports.isStale('invalid', 300000, now), true)
  assert.equal(exports.isStale('2026-10-16T06:00:00Z', 300000, now), true)
  assert.ok(exports.formatMetricTime('2026-10-15T06:00:00Z').includes('03:00:00'))
  assert.equal(exports.comparisonDelta(2, 0), 'Sem base percentual')
  assert.equal(exports.comparisonDelta(0, 0), 'Sem variação')
  assert.equal(exports.comparisonDelta(0, 2), '-100%')
  assert.equal(exports.comparisonDelta(3, 2), '+50%')
})
