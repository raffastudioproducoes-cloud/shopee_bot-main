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
  const api = read("api/billing.ts")
  assert.match(api, /"\/admin\/billing\/status"/)
  assert.match(api, /"\/admin\/billing\/webhook"/)
  assert.doesNotMatch(api, /ASAAS_API_KEY|access_token|aact_/)
})
