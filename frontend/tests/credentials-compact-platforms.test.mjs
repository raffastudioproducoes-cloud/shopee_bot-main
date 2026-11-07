import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"

const page = readFileSync(new URL("../src/pages/CredentialsPage.tsx", import.meta.url), "utf8")
const admin = readFileSync(new URL("../src/pages/AdminCredentialsPage.tsx", import.meta.url), "utf8")
const styles = readFileSync(new URL("../src/index.css", import.meta.url), "utf8")
const platforms = readFileSync(new URL("../src/lib/credentialPlatforms.ts", import.meta.url), "utf8")

test("abas lojas e redes sociais, com card compacto e ajuda expansível", () => {
  assert.match(page, /activeTab.*useState<CredentialTab>\("stores"\)/)
  assert.match(page, /role="tablist"/)
  assert.match(page, /role="tabpanel"/)
  assert.match(page, /<details className="credential-help">/)
  assert.match(page, /<summary>/)
  assert.match(page, /aria-expanded=\{!collapsed\}/)
  assert.match(page, /localStorage\.getItem\(COLLAPSE_KEY \+ id\) !== "0"/)
  assert.match(styles, /credentials-card-grid/)
  assert.match(page, /key: "shopee-video",\s*title: "Shopee Vídeo",\s*category: "social"/)
  assert.match(page, /key: "shopee",\s*title: "Shopee",\s*category: "stores"/)
})

test("botão testar conexão sai da página comum e vira teste único no diagnóstico ADMIN", () => {
  assert.doesNotMatch(page, /credentialsApi\.testConnection|Testar conexão"\}/)
  assert.match(admin, /credentialsApi\.testAllAdminConnections/)
  assert.match(admin, /Testar todas as conexões/)
  assert.doesNotMatch(admin, /credentialsApi\.testConnection/)
})

test("lojas futuras e Telegram/WhatsApp aparecem como informativos sem persistência fictícia", () => {
  for (const key of ["amazon", "americanas", "aliexpress", "awin", "lomadee", "magalu", "mercadolivre", "natura-avon", "prospin", "rakuten", "shein", "terabyteshop", "telegram", "whatsapp"]) {
    assert.match(platforms, new RegExp(`key: "${key}"`))
  }
  assert.match(page, /FUTURE_CREDENTIAL_PLATFORMS\.map/)
  assert.match(page, /<StatusBadge tone="warning">Em breve<\/StatusBadge>/)
  const future = page.slice(page.indexOf("function FutureCredentialCard"), page.indexOf("// ── Card do Threads"))
  assert.doesNotMatch(future, /useMutation|credentialsApi|TextInput/)
})

test("logos reais das marcas estão incluídos localmente sem chamada externa em tempo de execução", () => {
  const assets = [...platforms.matchAll(/"([a-z-]+\.(?:svg|png))"/g)].map(m => m[1])
  assert.ok(assets.length >= 18)
  for (const asset of assets) {
    const url = new URL(`../public/brand-logos/${asset}`, import.meta.url)
    assert.ok(existsSync(url), `Logo ${asset} precisa existir`)
  }
  assert.match(page, /src=\{`\/brand-logos\/\$\{logo\}`\}/)
})
