import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../src/pages/CredentialsPage.tsx", import.meta.url), "utf8")
const registryStart = source.indexOf("  const cards: {")
const registryEnd = source.indexOf("  const grouped = groupCredentialCards(cards.filter(", registryStart)
const registry = source.slice(registryStart, registryEnd)

test("os oito cards das redes integram o agrupamento, sem chave IA na página comum", () => {
  assert.ok(registryStart >= 0 && registryEnd > registryStart)
  const cards = ["Facebook", "Instagram", "Kwai",
    "Shopee Vídeo", "Threads", "TikTok", "X (Twitter)"]
  for (const title of cards) {
    assert.equal(registry.split('title: "' + title + '"').length - 1, 1, `Card ${title} deve aparecer uma vez`)
  }
  assert.doesNotMatch(registry, /Inteligência Artificial|AiCredentialCard/)
  assert.match(registry, /title: "Shopee"[^]*?<ShopeeAffiliateCredentialCard/)
  assert.match(source, /ID do afiliado \(ou link completo com o ID\)/)
  assert.doesNotMatch(source.slice(source.indexOf('function ShopeeAffiliateCredentialCard'), source.indexOf('function KwaiComingSoonCredentialCard')), /label="(App ID|Secret)"/)
  assert.doesNotMatch(source, /function SimpleCredentialCard|pegar App ID\/Secret/)
  assert.match(source, /groupCredentialCards\(cards\.filter\(\(card\) => card\.category === activeTab\)\)/)
  assert.match(source, /role="tablist"/)
  assert.match(source, /role="tabpanel"/)
  assert.match(source, /title: "Já credenciados"[^]*?title: "Ainda não cadastrados"/)
  assert.match(source, /grouped\.registered[^]*?grouped\.pending/)
  assert.match(source, /aria-labelledby=\{`credentials-\$\{group\.id\}`\}/)
  assert.match(source, /credentials-card-grid csp-named-card-grid/)
})

test("Shopee Vídeo é card informativo, recolhível e sem conexão fictícia", () => {
  const start = source.indexOf("function ShopeeVideoCredentialCard()")
  const end = source.indexOf("// ── Card do Threads", start)
  assert.ok(start > 0 && end > start)
  const card = source.slice(start, end)
  assert.match(card, /<CredPanel id="Shopee Vídeo">/)
  assert.match(card, /<CredHeader[^]*?title="Shopee Vídeo"/)
  assert.match(card, /Aguardando aprovação/)
  assert.match(card, /Shopee Afiliados[^]*?não autorizam a publicação de vídeos/)
  assert.match(card, /<Button type="button" variant="primary" disabled>\s*Conectar Shopee Vídeo/)
  assert.doesNotMatch(card, /credentialsApi|useMutation|authorize|appId|secret/i)
})
