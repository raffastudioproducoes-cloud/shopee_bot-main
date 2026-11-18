import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8")

test("Cobrança tem aba própria no painel ADMIN, separada de Diagnóstico", () => {
  const layout = read("pages/AdminLayout.tsx")
  assert.match(layout, /to: '\/admin\/billing', label: 'Cobrança'/)
  assert.match(layout, /to: '\/admin\/credentials', label: 'Diagnóstico'/)
  const router = read("router.tsx")
  assert.match(router, /path: "billing"/)
  assert.match(router, /getParentRoute: \(\) => adminRoute,\s+path: "billing"/)
})

test("o painel de cobrança não aparece mais em Configurações do cliente", () => {
  assert.doesNotMatch(read("components/plans/PlanComparison.tsx"), /BillingAdminPanel/)
  assert.match(read("pages/AdminBillingPage.tsx"), /BillingAdminPanel/)
})

test("rotas do painel ficam em /admin/billing e não expõem segredo", () => {
  const api = read("api/billingAdmin.ts")
  assert.match(api, /"\/admin\/billing\/status"/)
  assert.match(api, /"\/admin\/billing\/webhook"/)
  assert.doesNotMatch(api, /ASAAS_API_KEY|access_token|aact_/)
})

test("o pacote do cliente não importa o arquivo de API do ADMIN", () => {
  for (const file of ["api/billing.ts", "pages/PlanosPage.tsx", "components/plans/PlanCheckout.tsx", "components/plans/SubscriptionCard.tsx", "pages/presentation/Offer.tsx"]) {
    assert.doesNotMatch(read(file), /from "[^"]*billingAdmin"/, `${file} importa a API do ADMIN`)
  }
  assert.match(read("components/plans/BillingAdminPanel.tsx"), /api\/billingAdmin/)
})

test("sem chave o painel diz Não configurado, não Sandbox", () => {
  const panel = read("components/plans/BillingAdminPanel.tsx")
  assert.match(panel, /s\.environment \? ENV_NAMES\[s\.environment\] : "Não configurado"/)
  assert.match(panel, /s\.environment === "sandbox" && <><dt>Contas de teste/)
  assert.match(read("api/billingAdmin.ts"), /environment: "sandbox" \| "production" \| null/)
})

test("botão do webhook explica o que falta e para onde a URL aponta", () => {
  const panel = read("components/plans/BillingAdminPanel.tsx")
  assert.match(panel, /Defina ASAAS_API_KEY e ASAAS_WEBHOOK_TOKEN no Render para habilitar o webhook\. Falta: \{missing\.join\(" e "\)\}/)
  assert.match(panel, /"ASAAS_API_KEY"/)
  assert.match(panel, /"ASAAS_WEBHOOK_TOKEN"/)
  assert.match(panel, /disabled=\{missing\.length > 0/)
  assert.match(panel, /ASAAS_API_URL aponta para \{ENV_NAMES\[s\.api_url_environment\]\}/)
  assert.match(panel, /environment_mismatch/)
})
