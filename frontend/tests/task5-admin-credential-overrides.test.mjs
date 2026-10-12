import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('common credentials page lazy-loads the administrative override module only for ADMIN', async () => {
  const page = await source('pages/CredentialsPage.tsx')

  assert.match(page, /lazy\(\(\)\s*=>\s*import\(["']\.\.\/components\/credentials\/AdminOverrides["']\)/)
  assert.match(page, /isAdmin\s*&&\s*\(\s*<Suspense[\s\S]*<AdminOverrides/)
})

test('common credentials source has no manual social token controls or developer portal copy', async () => {
  const page = await source('pages/CredentialsPage.tsx')
  const api = await source('api/credentials.ts')

  assert.doesNotMatch(page, /override manual|Salvar \(override manual\)|portal de desenvolvedores|Open ID|Threads User ID/i)
  assert.doesNotMatch(api, /saveThreads|saveXManual|saveFacebookManual|saveTiktokManual|saveInstagramManual|CREDENTIAL_HELP_LINKS/)
})

test('the administrative module owns the manual endpoints and developer diagnostics', async () => {
  const overrides = await source('components/credentials/AdminOverrides.tsx')
  const adminApi = await source('api/credentialsAdmin.ts')

  assert.match(overrides, /Portal de desenvolvedores/i)
  assert.match(overrides, /Salvar override/i)
  assert.match(adminApi, /credentials\/threads/)
  assert.match(adminApi, /credentials\/x\/manual/)
})
