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
  let visitingSite = false



  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useLayoutEffect() {}, useRef: () => ({ current: null }), useState: value => [value, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-router') return { Link: 'Link', Outlet: 'Outlet', useLocation: () => ({ pathname: '/admin/users' }), useNavigate: () => () => {} }
    if (name === '@tanstack/react-query') return { useQuery: () => ({ data: { data: [] }, isLoading: false }) }
    if (name === '../stores/authStore') return { useAuthStore: selector => selector({ user: { username: 'Admin', access: 'ADMIN' }, logout() {} }) }
    if (name === '../lib/adminSiteFlag') return { setAdminVisitingSite: () => { visitingSite = true } }
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
  const zones = header.props.children.filter(Boolean)
  assert.equal(zones.length, 3, 'cabeçalho deve ter apenas marca, menu e ações; a casa não pode criar uma quarta coluna')
  const actions = zones.find(node => node.props?.className === 'admin-header-actions')
  assert.ok(actions, 'casa e conta devem dividir o mesmo grupo à direita')
  const site = nodes(actions).find(node => node.type === 'Link' && node.props.to === '/')
  assert.ok(site, 'manter acesso ao site')
  assert.equal(site.props['aria-label'], 'Ir para o site de cliente')
  assert.ok(site.props.onClick, 'preservar a flag que permite ao ADMIN visitar o site')
  site.props.onClick()
  assert.equal(visitingSite, true)
  assert.ok(nodes(actions).some(node => node.props?.className === 'admin-account'))
  const links = nodes(navigation).filter(node => node.type === 'Link')
  assert.equal(links.length, 4)
  assert.ok(links.every(node => node.props['aria-label']))
  assert.equal(links.find(node => node.props.to === '/admin/users').props['aria-current'], 'page')
  assert.ok(rendered.some(node => node.type === 'aside'))
  assert.equal(rendered.filter(node => node.type === 'nav').length, 1, 'somente o menu superior deve navegar entre seções')
  assert.ok(rendered.filter(node => node.type === 'Link' && node.props.to !== '/').every(node => node.props.to.startsWith('/admin')), 'navegação do admin não deve incluir funções comuns (exceto o link "Ir para o site")')
})
