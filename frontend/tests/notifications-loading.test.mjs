import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('notificações anunciam o carregamento mesmo com placeholders decorativos', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/components/ui/NotificationsBell.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useEffect() {}, useRef: () => ({}), useState: () => [true, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-query') return { useQuery: () => ({ isLoading: true }) }
    if (name === '../../stores/notificationsStore') return { useNotificationsStore: () => null }
    return new Proxy({}, { get: (_, key) => key })
  } })
  function nodes(node) {
    if (Array.isArray(node)) return node.flatMap(nodes)
    if (!node || typeof node !== 'object') return []
    return [node, ...nodes(node.props?.children)]
  }
  const status = nodes(exports.NotificationsBell()).find(node => node.props?.role === 'status')
  assert.ok(status, 'carregamento sem região de status')
  assert.equal(status.props['aria-busy'], true)
  assert.equal(status.props['aria-label'], 'Carregando notificações')
})
