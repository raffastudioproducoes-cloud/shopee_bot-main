import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('admin coloca navegação no topo e mantém coluna de apoio com links acessíveis', () => {
  const file = new URL('../src/pages/AdminLayout.tsx', import.meta.url)
  assert.ok(existsSync(file), 'layout administrativo superior ausente')
  const code = ts.transpileModule(readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  let tooltipDismissed = false
  let documentKeydown
  const effects = []
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, document: { addEventListener(event, handler) { documentKeydown = handler }, removeEventListener() {} }, require(name) {
    if (name === 'react') return { useEffect: callback => effects.push(callback), useLayoutEffect() {}, useRef: () => ({ current: null }), useState: value => [value, next => { tooltipDismissed = next }] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-router') return { Link: 'Link', Outlet: 'Outlet', useLocation: () => ({ pathname: '/admin/users' }), useNavigate: () => () => {} }
    if (name === '@tanstack/react-query') return { useQuery: () => ({ data: { data: [] }, isLoading: false }) }
    if (name === '../stores/authStore') return { useAuthStore: selector => selector({ user: { username: 'Admin', access: 'ADMIN' }, logout() {} }) }
    return new Proxy({}, { get: (_, key) => key })
  } })
  function nodes(node) {
    if (Array.isArray(node)) return node.flatMap(nodes)
    if (!node || typeof node !== 'object') return []
    return [node, ...nodes(node.props?.children)]
  }
  const rendered = nodes(exports.AdminLayout())
  const header = rendered.find(node => node.type === 'header')
  const navigation = nodes(header).find(node => node.type === 'nav')
  assert.ok(navigation, 'menu deve estar dentro do cabeçalho')
  const links = nodes(navigation).filter(node => node.type === 'Link')
  assert.equal(links.length, 4)
  assert.ok(links.every(node => node.props['aria-label']))
  assert.equal(links.find(node => node.props.to === '/admin/users').props['aria-current'], 'page')
  assert.ok(rendered.some(node => node.type === 'aside'))
  const dock = rendered.find(node => node.type === 'nav' && node.props['aria-label'] === 'Atalhos administrativos')
  assert.ok(dock, 'dock de atalhos da referência ausente')
  assert.equal(nodes(dock).filter(node => node.type === 'Link').length, 4)
  assert.ok(rendered.filter(node => node.type === 'Link').every(node => node.props.to.startsWith('/admin')), 'navegação do admin não deve incluir funções comuns')
  effects.forEach(effect => effect())
  assert.equal(typeof documentKeydown, 'function', 'Escape deve descartar tooltip mesmo com foco fora do dock')
  documentKeydown({ key: 'Escape' })
  assert.equal(tooltipDismissed, true)
  assert.ok(rendered.some(node => node.props?.['aria-label'] === 'Painel de apoio'))
})
