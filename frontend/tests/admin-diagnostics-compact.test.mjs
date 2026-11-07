import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('duas credenciais globais recolhíveis e sem testes individuais', () => {
  const page = source('pages/AdminCredentialsPage.tsx')
  const ai = source('components/credentials/AdminAiCredentialCard.tsx')
  const shopee = source('components/credentials/AdminShopeeCredentialCard.tsx')
  assert.match(page, /className="admin-platform-grid"/)
  for (const card of [ai, shopee]) {
    assert.match(card, /<details className="admin-platform-card">/)
    assert.match(card, /<summary className="admin-platform-card__header/)
    assert.doesNotMatch(card, /Testar conexão/)
  }
  assert.match(ai, /brand-logos\/gemini.svg/)
  assert.match(shopee, /brand-logos\/shopee.svg/)
  const css = source('styles/admin.css')
  assert.match(css, /admin-platform-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2/)
  assert.match(css, /max-width:\s*1200px[^}]*admin-platform-grid/)
  assert.match(page, /Testar todas as conexões/)
  assert.doesNotMatch(page, /testConnection\(/)
  assert.doesNotMatch(page, /AdminOverrides/)
})

test('estados reais usam logos, ordem alfabética e endpoint de teste em lote', () => {
  const page = source('pages/AdminCredentialsPage.tsx')
  const api = source('api/credentials.ts')
  assert.match(page, /buildAdminDiagnosticSections\(\)/)
  assert.match(page, /CATALOG\.stores\.map\(/)
  assert.match(page, /CATALOG\.social\.map\(/)
  assert.match(page, /CREDENTIAL_BRAND_LOGOS\[platform\.key\]/)
  assert.match(page, /planned \? plannedLabel/)
  assert.match(page, /platform\.key === 'shopee-video' \? 'OAuth em homologação' : 'Em breve'/)
  assert.match(page, /lastBatch\?\.results\[platform\.key\]/)
  assert.match(page, /platform\.availability === 'active'/)
  assert.match(page, /item\.state === 'error'/)
  assert.match(page, /ok: failed === 0/)
  assert.match(api, /api\.post\('\/admin\/credentials\/test-all'/)
  assert.match(page, /invalidateQueries\(\{ queryKey: \['admin', 'recent-logs'\]/)
})
