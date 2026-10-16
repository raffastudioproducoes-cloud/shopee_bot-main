import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('capacidade usa unidades compatíveis e amostras contemporâneas', () => {
  const exports = {}
  const source = readFileSync(new URL('../src/components/admin/metricsPresentation.ts', import.meta.url), 'utf8')
  runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports })
  const point = (value, unit, timestamp = '2026-10-15T12:00:00Z') => ({ value, unit, timestamp })
  assert.equal(exports.capacityPercent(point(256, 'MiB'), point(512 * 1048576, 'bytes')), 50)
  assert.equal(exports.capacityPercent(point(0.1, 'cpu'), point(0.2, 'CPU')), 50)
  assert.equal(exports.capacityPercent(point(100, 'bytes'), point(0, 'bytes')), null)
  assert.equal(exports.capacityPercent(point(100, 'bytes'), point(200, 'CPU')), null)
  assert.equal(exports.capacityPercent(point(100, 'bytes'), point(200, 'bytes', '2026-10-14T00:00:00Z')), null)
})
