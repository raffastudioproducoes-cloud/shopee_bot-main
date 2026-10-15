import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('diagnóstico acompanha o resultado assíncrono das credenciais', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/pages/AdminCredentialsPage.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  let query
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useState: value => [value, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    if (name === '@tanstack/react-query') return { useQueryClient: () => ({}), useQuery(options) { query = options; return { data: { threads: { state: 'testing', status_text: 'Verificando' } } } } }
    if (name === '@tanstack/react-router') return { useNavigate: () => () => {} }
    if (name === '../stores/authStore') return { useAuthStore: () => () => {} }
    return new Proxy({}, { get: (_, key) => key })
  } })
  exports.default()
  assert.ok(query, 'diagnóstico sem consulta ativa do resultado')
  assert.equal(query.refetchInterval({ state: { data: { threads: { state: 'testing' } } } }), 1500)
  assert.equal(query.refetchInterval({ state: { data: { threads: { state: 'ok' } } } }), false)
})
