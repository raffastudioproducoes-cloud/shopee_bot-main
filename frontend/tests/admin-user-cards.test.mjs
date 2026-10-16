import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('contas usam cards e indicadores derivados somente da página carregada', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/pages/UsersPage.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  let search = ''
  let role = 'ALL'
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === 'react') return { useState: value => [value === '' ? search : value === 'ALL' ? role : value, () => {}] }
    if (name === '@tanstack/react-router') return { useNavigate: () => () => {} }
    if (name === '@tanstack/react-query') return {
      useQueryClient: () => ({}), useMutation: () => ({}), useQuery: () => ({ data: { data: [
        { id: 'a', username: 'Conta A', access: 'ADMIN', created_at: '2026-10-15', updated_at: null },
        { id: 'b', username: 'Conta B', access: 'USER', created_at: '2026-10-14', updated_at: '2026-10-15' },
      ] } }),
    }
    if (name === '../stores/authStore') return { useAuthStore: () => () => {} }
    if (name === '../api/users') return { usersApi: {} }
    return new Proxy({}, { get: (_, key) => key })
  } })
  function nodes(node) {
    if (Array.isArray(node)) return node.flatMap(nodes)
    if (!node || typeof node !== 'object') return []
    return [node, ...nodes(node.props?.children)]
  }
  const rendered = nodes(exports.default())
  assert.equal(rendered.filter(node => node.type === 'article').length, 2)
  assert.deepEqual(rendered.filter(node => node.props?.['data-stat-value']).map(node => node.props.children), ['2', '1', '1', '1'])
  assert.ok(rendered.some(node => node.props?.label === 'Editar Conta A'))
  search = 'Conta B'
  assert.equal(nodes(exports.default()).filter(node => node.type === 'article').length, 1)
  search = ''
  role = 'ADMIN'
  assert.equal(nodes(exports.default()).filter(node => node.type === 'article').length, 1)
})
