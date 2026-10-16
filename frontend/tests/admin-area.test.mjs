import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('área admin tem guarda própria e rejeita USER antes de carregar páginas', async () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/router.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const routes = []
  let role = 'USER'
  const route = options => { const value = { ...options, addChildren() { return value } }; routes.push(value); return value }
  runInNewContext(code, { exports: {}, require(name) {
    if (name === 'react') return { lazy: () => 'lazy' }
    if (name === '@tanstack/react-router') return { createRootRoute: route, createRoute: route, createRouter: () => ({}), redirect: value => value }
    if (name === './api/auth') return { authApi: { me: async () => ({ access: role }) } }
    if (name === './stores/authStore') return { useAuthStore: { getState: () => ({ logout() {}, setUser() {}, setRoleVerified() {} }) } }
    return {}
  } })
  const admin = routes.find(value => value.path === '/admin')
  assert.ok(admin, 'área /admin ausente')
  await assert.rejects(admin.beforeLoad, value => value.to === '/')
  role = 'ADMIN'
  await admin.beforeLoad()
  for (const path of ['overview', 'users', 'logs', 'credentials']) {
    assert.ok(routes.some(value => value.path === path && value.getParentRoute() === admin), `filha admin ausente: ${path}`)
  }
})
