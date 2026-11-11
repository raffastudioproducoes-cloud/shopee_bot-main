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
