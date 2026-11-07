import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const catalog = readFileSync(new URL('../src/lib/analyticsNetworks.ts', import.meta.url), 'utf8')
const credentials = readFileSync(new URL('../src/lib/credentialPlatforms.ts', import.meta.url), 'utf8')
const page = readFileSync(new URL('../src/pages/AnalyticsPage.tsx', import.meta.url), 'utf8')
const visuals = readFileSync(new URL('../src/components/AnalyticsVisuals.tsx', import.meta.url), 'utf8')

test('Análises usa somente o catálogo de redes sociais de Credenciais, com nove plataformas', () => {
  assert.match(catalog, /buildAdminDiagnosticSections\(\)\.social/)
  assert.match(credentials, /\{ key: "telegram", title: "Telegram", category: "social"/)
  assert.match(credentials, /\{ key: "whatsapp", title: "WhatsApp", category: "social"/)
  for (const key of ['facebook', 'instagram', 'kwai', 'shopee-video', 'telegram', 'threads', 'tiktok', 'whatsapp', 'x']) {
    assert.match(catalog, new RegExp(`(?:^|\\n)\\s*(?:'${key}'|${key}): \\{ label:`, 'm'))
  }
  assert.doesNotMatch(catalog, /\b(?:amazon|mercadolivre|aliexpress): \{ label:/)
  assert.match(page, /ANALYTICS_NETWORKS\.map\(\(platform\) =>/)
  assert.match(page, /aria-pressed=\{network === platform\.key\}/)
  assert.match(page, /\/brand-logos\/\$\{logo\}/)
})

test('redes não integradas nunca chamam endpoints incompatíveis nem inventam métricas', () => {
  assert.match(catalog, /ANALYTICS_RECORDED_NETWORKS = \['facebook', 'instagram', 'threads', 'tiktok', 'x'\]/)
  assert.match(page, /const filterAvailable = network === 'all' \|\| hasRecordedAnalytics\(network\)/)
  assert.equal((page.match(/enabled: Boolean\(userId\) && canQuerySelection && filterAvailable/g) ?? []).length, 3)
  assert.match(page, /if \(selectedProfile === 'all' \|\| refreshing \|\| !filterAvailable\) return/)
  assert.match(page, /Não há coleta externa habilitada para esta rede/)
  assert.match(page, /Não há coleta externa habilitada[\s\S]*?nenhuma consulta à API da plataforma é realizada/)
  assert.match(visuals, /ANALYTICS_RECORDED_NAMES/)
})
