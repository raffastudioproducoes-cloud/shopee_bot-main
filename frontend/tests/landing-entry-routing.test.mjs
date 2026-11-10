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
  // ADM entra no site (dashboard) como qualquer conta; o painel admin é acessado pelo menu.
  const landing = router.match(/const landingRoute = createRoute\(\{[\s\S]*?component:\s*PresentationPage/)?.[0] ?? ''
  assert.doesNotMatch(landing, /admin\/overview|isAdminVisitingSite/)
})

test('dashboard usa app e guard existente, sem ocupar a raiz', async () => {
  const router = await source('router.tsx')
  const panel = await source('pages/PanelPage.tsx')
  const dashboard = router.match(/const dashboardRoute = createRoute\(\{[\s\S]*?\n\}\)/)?.[0] ?? ''
  assert.match(dashboard, /path:\s*["']\/app["']/)
  assert.doesNotMatch(dashboard, /admin\/overview/, 'ADM não é desviado do dashboard')
  assert.match(panel, /authApi\.me\(\)/)
  assert.match(panel, /value:\s*["']\/app["'],\s*label:\s*["']Dashboard["']/)
})

test('login por senha ou Google e atalho admin respeitam nova rota', async () => {
  const login = await source('pages/LoginPage.tsx')
  const admin = await source('pages/AdminLayout.tsx')
  assert.doesNotMatch(login, /admin\/overview/, 'login de ADM vai para o dashboard')
  assert.equal((login.match(/navigate\(\{ to: '\/app' \}\)/g) ?? []).length >= 2, true)
  assert.match(admin, /<Link\s+to=["']\/app["']\s+className=["']admin-site-link["']\s+onClick=\{setAdminVisitingSite\}/)
})
