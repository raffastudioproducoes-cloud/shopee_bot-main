import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('painel mantém indicador visível enquanto a sessão aguarda validação', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/pages/PanelPage.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useEffect() {}, useRef: () => ({}), useState: () => [false, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx: (type, props) => ({ type, props }) }
    if (name === '@tanstack/react-router') return { useNavigate: () => () => {}, useLocation: () => ({ pathname: '/' }) }
    if (name === '../stores/authStore') return { useAuthStore: () => ({ isAuthenticated: true, isRoleVerified: false }) }
    return new Proxy({}, { get: (_, key) => key })
  } })
  const view = exports.PanelPage()
  assert.ok(view, 'sessão pendente deixou a página vazia')
  assert.ok(['OrbitalLoader', 'PageSkeleton'].includes(view.type))
})
