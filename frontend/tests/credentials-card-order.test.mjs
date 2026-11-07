import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../src/pages/CredentialsPage.tsx", import.meta.url), "utf8")
const gridStart = source.lastIndexOf('<div className="credentials-card-grid csp-named-card-grid">')
const gridEnd = source.indexOf("\n      </div>", gridStart)
const grid = source.slice(gridStart, gridEnd)

test("cards de Credenciais seguem a ordem alfabética dos títulos em PT-BR", () => {
  const entries = [
    ["Facebook", "<FacebookCredentialCard"],
    ["Instagram", "<InstagramCredentialCard"],
    ["Inteligência Artificial", "<AiCredentialCard"],
    ["Kwai", 'network="kwai"'],
    ["Shopee", "{SIMPLE_NETWORKS.map("],
    ["Shopee Vídeo", "<ShopeeVideoCredentialCard"],
    ["Threads", "<ThreadsCredentialCard"],
    ["TikTok", "<TikTokCredentialCard"],
    ["X (Twitter)", "<XCredentialCard"],
  ]
  const collator = new Intl.Collator("pt-BR", { sensitivity: "base" })
  assert.deepEqual(entries.map(([name]) => name), entries.map(([name]) => name).sort(collator.compare))
  const positions = entries.map(([name, anchor]) => {
    const index = grid.indexOf(anchor)
    assert.ok(index >= 0, `Card ausente: ${name}`)
    return index
  })
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b))
  assert.match(source, /const SIMPLE_NETWORKS[^]*?key: "shopee", label: "Shopee"/)
})

test("Shopee Vídeo é card informativo, recolhível e sem conexão fictícia", () => {
  const start = source.indexOf("function ShopeeVideoCredentialCard()")
  const end = source.indexOf("// ── Card da chave de IA", start)
  assert.ok(start > 0 && end > start)
  const card = source.slice(start, end)
  assert.match(card, /<CredPanel id="Shopee Vídeo">/)
  assert.match(card, /<CredHeader[^]*?title="Shopee Vídeo"/)
  assert.match(card, /Aguardando aprovação/)
  assert.match(card, /Shopee Afiliados[^]*?não autorizam a publicação de vídeos/)
  assert.match(card, /<Button type="button" variant="primary" disabled>\s*Conectar Shopee Vídeo/)
  assert.doesNotMatch(card, /credentialsApi|useMutation|authorize|appId|secret/i)
})
