import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')
test('profiles stays a common page without user-management code', async () => {
  const profiles = await source('pages/ProfilesPage.tsx')
  assert.doesNotMatch(profiles, /usersApi|AppUser|UserAccess|Contas de login|administra..o de contas/i)
})
test('admin routes are guarded before their chunks can load', async () => {
  const router = await source('router.tsx')
  assert.doesNotMatch(router, /import\s+\{\s*(LogsPage|UsersPage)\s*\}\s+from/)
  assert.match(router, /lazy\(\(\)\s*=>\s*import\(["']\.\/pages\/UsersPage["']\)/)
  assert.match(router, /lazy\(\(\)\s*=>\s*import\(["']\.\/pages\/LogsPage["']\)/)
  assert.match(router, /beforeLoad:\s*requireAdmin/)
  assert.match(router, /await authApi\.me\(\)/)
  assert.match(router, /throw redirect\(\{\s*to:\s*["']\/["']\s*}\)/)
})
test('bootstrap revalidates the server role before rendering the panel', async () => {
  const panel = await source('pages/PanelPage.tsx')
  const authStore = await source('stores/authStore.ts')
  assert.match(panel, /authApi\.me\(\)/)
  assert.doesNotMatch(panel, /if\s*\(!user\)\s*\{\s*authApi\.me\(\)/)
  assert.match(panel, /if\s*\(!isRoleVerified\)\s*\{\s*return null/)
  assert.match(authStore, /isRoleVerified:\s*false/)
  assert.match(authStore, /setRoleVerified/)
})
test('profiles is visible to every authenticated user while admin links are conditional', async () => {
  const panel = await source('pages/PanelPage.tsx')
  assert.match(panel, /const navItems[\s\S]*value:\s*['"]\/profiles['"].*label:\s*['"]Perfis['"]/)
  assert.match(panel, /const adminNavItems[\s\S]*value:\s*['"]\/users['"][\s\S]*value:\s*['"]\/logs['"]/)
})