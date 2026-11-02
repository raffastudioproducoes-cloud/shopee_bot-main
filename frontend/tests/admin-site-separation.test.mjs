import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('flag de visita ao site usa sessionStorage protegido por try/catch', async () => {
  const flag = await source('lib/adminSiteFlag.ts')
  assert.match(flag, /orbital:admin-visiting-site/)
  assert.equal((flag.match(/try\s*\{/g) ?? []).length >= 3, true)
  assert.match(flag, /sessionStorage/)
})

test('login e rota /app enviam ADMIN para /admin/overview, respeitando a flag', async () => {
  const login = await source('pages/LoginPage.tsx')
  const router = await source('router.tsx')
  const panel = await source('pages/PanelPage.tsx')
  assert.match(login, /user\.access\s*===\s*['"]ADMIN['"][\s\S]*\/admin\/overview/)
  assert.match(login, /clearAdminVisitingSite\(\)/)
  const dash = router.match(/const dashboardRoute = createRoute\(\{[\s\S]*?\r?\n}\)/)?.[0] ?? ''
  assert.match(dash, /beforeLoad/)
  assert.match(router, /ADMIN[\s\S]*isAdminVisitingSite\(\)[\s\S]*\/admin\/overview|isAdminVisitingSite\(\)[\s\S]*ADMIN[\s\S]*\/admin\/overview/)
  assert.match(panel, /isAdminVisitingSite\(\)/)
})

test('AdminLayout tem "Ir para o site" que grava a flag; site tem "Painel admin" que a limpa', async () => {
  const layout = await source('pages/AdminLayout.tsx')
  const panel = await source('pages/PanelPage.tsx')
  const store = await source('stores/authStore.ts')
  assert.match(layout, /Ir para o site/)
  assert.match(layout, /onClick=\{setAdminVisitingSite\}/)
  assert.match(panel, /label:\s*['"]Painel admin['"]/)
  assert.doesNotMatch(panel, /Administração/)
  assert.match(panel, /clearAdminVisitingSite\(\)/)
  assert.match(store, /clearAdminVisitingSite\(\)/)
})

test('403 em rota /admin revalida /auth/me e sai do admin sem loop', async () => {
  const api = await source('lib/api.ts')
  assert.match(api, /403/)
  assert.match(api, /startsWith\(['"]\/admin['"]\)/)
  assert.match(api, /setRoleVerified\(false\)/)
  assert.match(api, /\/auth\/me/)
})

test('site de cliente não tem UI admin nas credenciais nem logs/usuários com role redundante', async () => {
  const creds = await source('pages/CredentialsPage.tsx')
  const logs = await source('pages/LogsPage.tsx')
  const users = await source('pages/UsersPage.tsx')
  assert.doesNotMatch(creds, /comingSoonForNonAdmin|title={status.check_message|AdminOverrides/)
  assert.doesNotMatch(logs, /access\s*[!=]==\s*["']ADMIN["']/)
  assert.doesNotMatch(users, /state\.user\b|access\s*!==\s*.ADMIN.\)\s*return/)
})

test('endpoints de override manual ficam em /admin/credentials', async () => {
  const adminApi = await source('api/credentialsAdmin.ts')
  assert.match(adminApi, /['"]\/admin\/credentials\/threads['"]/)
  for (const n of ['x', 'facebook', 'tiktok', 'instagram', 'kwai']) assert.match(adminApi, new RegExp(`/admin/credentials/${n}/manual`))
  assert.doesNotMatch(adminApi, /put\(['"]\/credentials/)
})

test('métricas de usuários no globo ficam marcadas como "em breve" sem dado real inventado', async () => {
  const globe = await source('components/admin/LocationGlobe.tsx')
  assert.match(globe, /Em breve/)
})
