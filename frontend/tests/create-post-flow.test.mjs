import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"
import { canOfferPlanUpgrade, quotaBarText } from "../src/lib/quotaBarPresentation.ts"

const resource = (used, limit, unlimited = false) => ({
  used, limit, unlimited, usage_status: used === null ? "unavailable" : "available",
})
const plan = (overrides = {}) => ({
  plan_tier: "pro", is_admin: false, campaigns_enabled: true,
  active_campaigns_count: 2, active_campaigns_limit: 3,
  campaign_days: 14, campaign_posts_per_day: 5,
  resources: {
    products: resource(8, 10), lists: resource(4, 10),
    immediate: resource(null, 15), recurring: resource(null, 6),
  }, ...overrides,
})

test("upgrade não aparece em Premium ou na conta ADMIN", () => {
  assert.equal(canOfferPlanUpgrade(plan({ plan_tier: "free" })), true)
  assert.equal(canOfferPlanUpgrade(plan({ plan_tier: "pro" })), true)
  assert.equal(canOfferPlanUpgrade(plan({ plan_tier: "plus" })), true)
  assert.equal(canOfferPlanUpgrade(plan({ plan_tier: "premium" })), false)
  assert.equal(canOfferPlanUpgrade(plan({ is_admin: true })), false)
  assert.equal(canOfferPlanUpgrade(undefined), false)
})

test("publicações mostram limite conhecido sem inventar consumo", () => {
  const text = quotaBarText(plan(), "publishing", false, false)
  assert.equal(text.title, "Cota de publicações")
  assert.match(text.detail, /Enviar agora: 15\/hora/)
  assert.match(text.detail, /Recorrências: 6\/dia/)
  assert.doesNotMatch(text.detail, /Uso indisponível|0 \/ 15/)
})

test("campanhas mostram vagas/limites e respeitam indisponibilidade", () => {
  assert.match(quotaBarText(plan(), "campaigns", false, false).detail, /2 \/ 3 ativas/)
  assert.match(quotaBarText(plan(), "campaigns", false, false).detail, /14 dias/)
  assert.match(quotaBarText(plan({ campaigns_enabled: false }), "campaigns", false, false).detail, /não incluídas/)
  assert.match(quotaBarText(plan({ is_admin: true, active_campaigns_limit: null }), "campaigns", false, false).detail, /sem cota comercial/)
  assert.equal(quotaBarText(plan(), "campaigns", true, false).detail, "Consultando cota...")
  assert.equal(quotaBarText(plan(), "campaigns", false, true).detail, "Cota indisponível")
})

test("regressão: cópias compactas de Produtos e Listas permanecem", () => {
  assert.equal(quotaBarText(plan(), "products", false, false).detail, "8 de 10 utilizados")
  assert.equal(quotaBarText(plan(), "lists", false, false).detail, "4 de 10 utilizadas")
})

test("fluxo visual mantém etapas, ações e homologação após configuração e prévia", () => {
  const source = readFileSync(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  const steps = [
    "01. Produtos", "02. Período e frequência", "03. Prévia do calendário",
    "04. Rascunhos da campanha", "05. Ativar campanha", "06. Campanhas e entregas",
  ]
  let lastIndex = -1
  for (const step of steps) {
    const index = source.indexOf(step)
    assert.ok(index > lastIndex, `etapa ${step} fora de ordem`)
    lastIndex = index
  }
  assert.match(source, /Salvar rascunho/)
  assert.match(source, /Continuar rascunho salvo/)
  assert.match(source, /Confirmar exclusão/)
  assert.match(source, /Ativar campanha salva/)
  assert.match(source, /Ver histórico por rede/)
  assert.match(source, /href="#campaign-finalization"/)
  assert.doesNotMatch(source, /plan-campaign-lock|UpgradeInfo/)
  const page = readFileSync(new URL("../src/pages/CreatePostPage.tsx", import.meta.url), "utf8")
  assert.match(page, /resource=\{creationMode === "campaign" \? "campaigns" : "publishing"\}/)
  assert.doesNotMatch(page, /<PlanSummary/)
})
