import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile, readdir } from 'node:fs/promises'
const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('/admin e /admin/credentials redirecionam usuário comum pelo guard do pai', async () => {
  const router = await source('router.tsx')
  const guard = router.match(/async function requireAdmin\(\)[\s\S]*?\n}\n/)?.[0] ?? ''
  assert.match(guard, /user\.access\s*!==\s*["']ADMIN["'][\s\S]*throw redirect\(\{\s*to:\s*["']\/["']\s*}\)/)
  const admin = router.match(/const adminRoute = createRoute\(\{[\s\S]*?\n}\)/)?.[0] ?? ''
  assert.match(admin, /path:\s*["']\/admin["']/)
  assert.match(admin, /beforeLoad:\s*requireAdmin/)
  const creds = router.match(/const adminCredentialsRoute = createRoute\(\{[\s\S]*?\n}\)/)?.[0] ?? ''
  assert.match(creds, /getParentRoute:\s*\(\)\s*=>\s*adminRoute/)
})

test('frontend não busca nem exibe IP de logs', async () => {
  const files = (await readdir(new URL('../src/', import.meta.url), { recursive: true })).filter((f) => /\.(ts|tsx)$/.test(f) && !/PrivacyPolicy/.test(f))
  for (const file of files) assert.doesNotMatch(await source(file), /client_ip/, file)
})
