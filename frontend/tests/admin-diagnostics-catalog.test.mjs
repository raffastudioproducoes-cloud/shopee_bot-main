import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { transformSync } from 'esbuild'

const source = readFileSync(new URL('../src/lib/credentialPlatforms.ts', import.meta.url), 'utf8')
const { code } = transformSync(source, { loader: 'ts', format: 'esm', target: 'es2022' })
const { buildAdminDiagnosticSections } = await import(`data:text/javascript,${encodeURIComponent(code)}`)

test('diagnóstico contempla as doze lojas planejadas, sem marcá-las como funcionais', () => {
  const { stores } = buildAdminDiagnosticSections()
  assert.deepEqual(stores.map(platform => platform.key), [
    'aliexpress', 'amazon', 'americanas', 'magalu', 'mercadolivre',
    'natura-avon', 'prospin', 'awin', 'lomadee', 'rakuten', 'shein', 'terabyteshop',
  ])
  assert.ok(stores.every(platform => platform.availability === 'planned' && platform.category === 'stores'))
})

test('diagnóstico contempla seis redes existentes e três informativas em ordem alfabética', () => {
  const { social } = buildAdminDiagnosticSections()
  assert.deepEqual(social.map(platform => platform.key), [
    'facebook', 'instagram', 'kwai', 'shopee-video', 'telegram',
    'threads', 'tiktok', 'whatsapp', 'x',
  ])
  assert.deepEqual(social.filter(platform => platform.availability === 'planned').map(platform => platform.key), [
    'shopee-video', 'telegram', 'whatsapp',
  ])
  assert.equal(new Set([...social.map(platform => platform.key), ...buildAdminDiagnosticSections().stores.map(platform => platform.key)]).size, 21)
})
