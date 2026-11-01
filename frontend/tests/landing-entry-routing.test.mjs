import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('entrada publica valida cookie no backend e envia sessao real ao painel', async () => {
  const router = await source('router.tsx')
  assert.match(router, /const landingRoute = createRoute\(\{[\s\S]*?path:\s*["']\/["']/)
  assert.match(router, /const landingRoute = createRoute\(\{[\s\S]*?await authApi\.me\(\)/)
  assert.match(router, /const landingRoute = createRoute\(\{[\s\S]*?redirect\(\{\s*to:\s*["']\/app["']/)
  assert.match(router, /const landingRoute = createRoute\(\{[\s\S]*?component:\s*PresentationPage/)
  assert.match(router, /isAdminVisitingSite\(\)/)
  assert.match(router, /["']\/admin\/overview["']/)
})

test('dashboard usa app e guard existente, sem ocupar a raiz', async () => {
  const router = await source('router.tsx')
  const panel = await source('pages/PanelPage.tsx')
  const dashboard = router.match(/const dashboardRoute = createRoute\(\{[\s\S]*?\n\}\)/)?.[0] ?? ''
  assert.match(dashboard, /path:\s*["']\/app["']/)
  assert.match(dashboard, /beforeLoad:/)
  assert.match(panel, /authApi\.me\(\)/)
  assert.match(panel, /value:\s*["']\/app["'],\s*label:\s*["']Dashboard["']/)
})

test('login por senha ou Google e atalho admin respeitam nova rota', async () => {
  const login = await source('pages/LoginPage.tsx')
  const admin = await source('pages/AdminLayout.tsx')
  assert.match(login, /user\.access\s*===\s*["']ADMIN["']\s*\?\s*["']\/admin\/overview["']\s*:\s*["']\/app["']/)
  assert.match(admin, /<Link\s+to=["']\/app["']\s+className=["']admin-site-link["']\s+onClick=\{setAdminVisitingSite\}/)
})
