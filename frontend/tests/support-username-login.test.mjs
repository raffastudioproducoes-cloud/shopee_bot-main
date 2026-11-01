import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const loginSource = () => readFile(new URL('../src/pages/LoginPage.tsx', import.meta.url), 'utf8')
const backendSource = () => readFile(new URL('../../api/routers/auth.py', import.meta.url), 'utf8')

test('login usa campo texto para email ou usuario de suporte sem bloqueio nativo do navegador', async () => {
  const login = await loginSource()
  assert.match(login, /label=\{capabilities\.legacy_support_enabled\s*\?\s*['"]E-mail ou usuário de suporte['"]/)
  assert.match(login, /type=\{capabilities\.legacy_support_enabled\s*\?\s*['"]text['"]\s*:\s*['"]email['"]\}/)
  assert.match(login, /Para suporte Shopee, use o nome de usuário sem @/)
})

test('decisao pelo identificador envia email ao Supabase e username a rota restrita de suporte', async () => {
  const login = await loginSource()
  assert.match(login, /const useLegacyLogin = !capabilities\.email_enabled\s*\|\|[\s\S]*?capabilities\.legacy_support_enabled\s*&&\s*!username\.trim\(\)\.includes\(['"]@['"]\)/)
  assert.match(login, /if \(useLegacyLogin\) \{\s*await authApi\.login\(username\.trim\(\), password\)/)
  assert.match(login, /else \{\s*await authApi\.loginEmail\(username\.trim\(\), password\)/)
  assert.doesNotMatch(login, /legacySupportMode/)
})

test('backend ainda limita usuario e senha legados a conta configurada com papel USER', async () => {
  const backend = await backendSource()
  assert.match(backend, /allowed_username\s*=\s*settings\.supabase_legacy_support_username\.strip\(\)\.casefold\(\)/)
  assert.match(backend, /form_data\.username\.casefold\(\)\s*!=\s*allowed_username/)
  assert.match(backend, /user\.get\(["']access["']\)\s*!=\s*["']USER["']/)
})
