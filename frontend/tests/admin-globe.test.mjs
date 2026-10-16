import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('projeção esférica gira, oculta hemisfério traseiro e mantém escala', () => {
  const exports = {}
  const source = readFileSync(new URL('../src/components/admin/globeGeometry.ts', import.meta.url), 'utf8')
  runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports })
  const center = exports.projectGlobe(0, 0, 0, 0)
  assert.equal(center.x, 320)
  assert.equal(center.y, 250)
  assert.equal(center.visible, true)
  assert.equal(exports.projectGlobe(180, 0, 0, 0).visible, false)
  assert.equal(exports.projectGlobe(-43, -23, -43, -23).visible, true)
  const rotated = exports.projectGlobe(90, 0, 0, 0)
  assert.ok(Math.abs(rotated.x - 520) < 0.001)
  assert.equal(exports.clampZoom(100), 3)
  assert.equal(exports.clampZoom(0), 1)
  assert.ok(exports.wheelGlobeZoom(1, -120) > 1)
  assert.equal(exports.wheelGlobeZoom(1, 120), 1)
  assert.equal(exports.wheelGlobeZoom(3, -120), 3)
  assert.equal(exports.wheelGlobeZoom(1, -3, 1), exports.wheelGlobeZoom(1, -48, 0))
  assert.ok(exports.earthRotation(-45, 33) < -45)
  assert.ok(Math.abs(exports.earthRotation(-45, 10000) + 45.09) < .00001)
  const pole = exports.projectGlobe(0, 90, 0, 0, 1, 23.44)
  assert.ok(pole.x > 320 && pole.y < 250)
})

test('modo real sem coleta não desenha clientes nem usa a demonstração implicitamente', () => {
  const compile = file => ts.transpileModule(readFileSync(new URL(file, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const geometry = {}
  runInNewContext(compile('../src/components/admin/globeGeometry.ts'), { exports: geometry })
  const exports = {}
  const jsx = (type, props) => ({ type, props })
  runInNewContext(compile('../src/components/admin/LocationGlobe.tsx'), { exports, require(name) {
    if (name === 'react') return { useEffect: () => {}, useState: value => [value, () => {}], useId: () => 'test', useMemo: callback => callback(), useRef: value => ({ current: value }) }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === './globeGeometry') return geometry
    if (name === './globeLand.json') return { default: [[0, 0]] }
    if (name === './metricsPresentation') return { formatMetricTime: () => 'agora', isStale: () => false }
    return new Proxy({}, { get: (_, key) => key })
  } })
  const nodes = node => Array.isArray(node) ? node.flatMap(nodes) : node && typeof node === 'object' ? [node, ...nodes(node.props?.children)] : []
  const tree = exports.LocationGlobe({ data: { geography: { status: 'not_configured', regions: [{ region: 'BR-RJ', online: 123456, offline: 0, deleted: 0 }] } } })
  assert.ok(JSON.stringify(tree).includes('Nenhum ponto real é exibido'))
  assert.ok(!JSON.stringify(tree).includes('123456'))
  assert.ok(!nodes(tree).some(node => node.props?.className?.startsWith('admin-globe-point')))
  assert.ok(nodes(tree).some(node => node.props?.children === 'Explorar demonstração' && node.props?.['aria-pressed'] === false))
})
