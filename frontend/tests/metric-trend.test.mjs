import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('curva suave preserva amostras e escala zero sem inventar dados', () => {
  const file = new URL('../src/components/admin/MetricTrend.tsx', import.meta.url)
  assert.ok(existsSync(file), 'gráfico administrativo ausente')
  const code = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const exports = {}
  runInNewContext(code, { exports, require: () => ({}) })
  assert.equal(exports.trendGeometry([]), null)
  const curve = exports.trendGeometry([0, 10, 0])
  assert.equal(curve.maximum, 10)
  assert.ok(curve.line.includes('C'))
  assert.ok(curve.line.endsWith('480,128'))
  assert.equal(curve.points[1][1], 16)
  const flat = exports.trendGeometry([0, 0])
  assert.ok(flat.points.every(point => point[1] === 128))
  const timed = exports.trendGeometry([1, 2, 3], ['2026-10-15T00:00:00Z', '2026-10-15T01:00:00Z', '2026-10-15T04:00:00Z'])
  assert.equal(timed.points[1][0], 150)
})
