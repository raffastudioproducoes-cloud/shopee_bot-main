import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { createRequire } from "node:module"
import vm from "node:vm"
import ts from "typescript"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"

const require = createRequire(import.meta.url)
async function moduleAt(path, mocks = {}) {
  const source = await readFile(new URL("../src/" + path, import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } })
  const module = { exports: {} }
  vm.runInNewContext(outputText, { module, exports: module.exports,
    require: (name) => name in mocks ? mocks[name] : name.endsWith(".css") ? {} : require(name),
  })
  return module.exports
}
const resource = (used = null, limit = 100, unlimited = false) => ({
  used, limit, unlimited, usage_status: used === null ? "unavailable" : "available",
})
const plan = (tier = "free", admin = false) => ({
  plan_tier: tier, is_admin: admin, profile_id: "a",
  campaign_days: admin ? 30 : tier === "pro" ? 15 : tier === "free" ? 0 : 30,
  campaign_posts_per_day: admin ? null : tier === "pro" ? 3 : tier === "free" ? 0 : 15,
  campaigns_enabled: admin || tier !== "free", active_campaigns_limit: tier === "pro" ? 2 : 5,
  automation_entitled: admin || tier === "premium", automation_available: false, activation_available: false,
  resources: { products: resource(7), lists: resource(2, 20), profiles: resource(1, 1),
    immediate: resource(null, 1), recurring: resource(null, 1) },
})

test("plano canônico, alias Plus e ADMIN não derivam do perfil legado", async () => {
  const lib = await moduleAt("lib/planPresentation.ts")
  assert.equal(lib.accountPlanLabel(plan("plus")), "Pro")
  assert.equal(lib.accountPlanLabel(plan("free", true)), "Administrador")
  assert.equal(lib.accountPlanLabel(undefined), "Plano indisponível")
  assert.equal(lib.accountPlanLabel(plan("premium")), "Premium")
  assert.equal(lib.resourceAtLimit(resource(100, 100)), true)
  assert.equal(lib.resourceAtLimit(resource(101, 100)), true)
  assert.equal(lib.resourceAtLimit(resource(null, 100)), false)
  assert.equal(lib.resourceAtLimit(resource(100, null, true)), false)
  assert.equal(lib.usageLabel(resource(null, 3)), "Uso indisponível / 3")
  assert.equal(lib.usageLabel(resource(0, 3)), "0 / 3")
  assert.deepEqual(JSON.parse(JSON.stringify(lib.campaignUiCaps(plan("pro")))), { days: 15, posts: 3 })
  assert.deepEqual(JSON.parse(JSON.stringify(lib.campaignUiCaps(plan("premium")))), { days: 30, posts: 15 })
  assert.deepEqual(JSON.parse(JSON.stringify(lib.campaignUiCaps(plan("free", true)))), { days: 30, posts: 15 })
})

test("query muda por conta e perfil e não usa placeholder anterior", async () => {
  let account = "owner", profile = "a", verified = true, options
  const mod = await moduleAt("hooks/usePlanUsage.ts", {
    "@tanstack/react-query": { useQuery: (value) => { options = value; return value } },
    "../api/planUsage": { planUsageApi: { get() {} } },
    "../stores/authStore": { useAuthStore: (selector) => selector({ user: { id: account }, isRoleVerified: verified }) },
    "../stores/profileStore": { useProfileStore: (selector) => selector({ activeProfileId: profile }) },
  })
  mod.usePlanUsage()
  assert.equal(JSON.stringify(options.queryKey), '["plan-usage","owner","a"]')
  profile = "b"; mod.usePlanUsage()
  assert.equal(JSON.stringify(options.queryKey), '["plan-usage","owner","b"]')
  account = "other"; mod.usePlanUsage()
  assert.equal(JSON.stringify(options.queryKey), '["plan-usage","other","b"]')
  verified = false; mod.usePlanUsage(); assert.equal(options.enabled, false)
  account = undefined; profile = null; mod.usePlanUsage(); assert.equal(options.enabled, false)
  assert.equal(options.placeholderData, undefined)
  assert.equal(options.gcTime, 0)
  assert.equal(options.refetchOnWindowFocus, "always")
})

test("resumo renderiza escopo, consumo ausente, erro 503 e CTA sem checkout", async () => {
  const lib = await moduleAt("lib/planPresentation.ts")
  let query = { data: plan(), isError: false, isPending: false, refetch() {} }
  const box = (tag) => ({ children }) => React.createElement(tag, null, children)
  const mod = await moduleAt("components/plans/PlanSummary.tsx", {
    "./PlanTag": { PlanTag: ({ children }) => React.createElement("span", null, children), planTierOf: () => "free" },
    "../ui/Button": { Button: box("button") },
    // Link do roteador precisa de contexto de rota; aqui só importa que exista o destino
    "@tanstack/react-router": { Link: ({ to, children }) => React.createElement("a", { "data-to": to }, children) },
    "../ui/Panel": { Panel: box("section") }, "../ui/Skeleton": { Skeleton: box("div") },
    "../../hooks/usePlanUsage": { usePlanUsage: () => query },
    "../../hooks/useProfiles": { useProfiles: () => ({ activeProfile: { id: "a" } }) },
    "../../lib/planPresentation": lib,
  })
  let html = renderToStaticMarkup(React.createElement(mod.PlanSummary))
  assert.match(html, /Free/); assert.match(html, /Produtos · conta/); assert.match(html, /Listas · perfil/)
  assert.match(html, /Uso indisponível \/ 1/); assert.match(html, /Limite atingido/)
  assert.match(html, /aria-expanded="false"/); assert.match(html, /aria-controls=/)
  assert.doesNotMatch(html, /checkout|href=/)
  query = { ...query, isError: true }
  html = renderToStaticMarkup(React.createElement(mod.PlanSummary))
  assert.match(html, /Não foi possível consultar o plano/); assert.match(html, /Tentar novamente/)
  assert.doesNotMatch(html, /7 \/ 100|>Free</)
  query = { ...query, isError: false, data: undefined, isPending: true, fetchStatus: "fetching" }
  html = renderToStaticMarkup(React.createElement(mod.PlanSummary))
  assert.match(html, /aria-busy="true"/); assert.doesNotMatch(html, /7 \/ 100/)
})

test("campanha bloqueia somente novas mutações; leitura e exclusão permanecem", async () => {
  const source = await readFile(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  assert.match(source, /disabled=\{!canEditCampaign \|\| !saveInput/)
  assert.match(source, /disabled=\{!canEditCampaign \|\| !payload/)
  assert.match(source, /disabled=\{!canEditCampaign\}/)
  assert.match(source, /<CampaignProductMediaSelector productId=\{id\}/)
  assert.match(source, /length: caps.posts/)
  assert.match(source, /scheduleUsage\.exceedsActiveDayLimit/)
  assert.match(source, /scheduleUsage\.calendarDays > 210/)
  assert.match(source, /campaignAccessBlockReason/)
  assert.match(source, /preparationRetryAllowed/)
  assert.match(source, /active_campaigns_count >= plan\.active_campaigns_limit/)
  assert.match(source, /onError: \(\) =>/)
  assert.match(source, /currentSaveSignatureRef\.current === variables\.signature/)
  assert.match(source, /campaignsApi.getDraft\(id\)/)
  assert.match(source, /campaignsApi.deleteDraft\(id, revision\)/)
  assert.match(source, /campaignsApi.deleteMedia\(savedDraftId!, id\)/)
  assert.doesNotMatch(source, /<fieldset[^>]*disabled/)
})

test("automação distingue direito do plano de executor disponível", async () => {
  let query = { data: plan("premium"), isError: false, isPending: false }
  const box = ({ children }) => React.createElement("section", null, children)
  const mod = await moduleAt("pages/PostsAutomationPage.tsx", {
    "../components/ui/Icon": { Icon: () => null }, "../components/ui/Panel": { Panel: box },
    "../components/ui/Button": { Button: box }, "../components/ui/Skeleton": { Skeleton: box },
    "../components/plans/PlanSummary": { PlanBadge: () => null, UpgradeInfo: () => null },
    "../hooks/usePlanUsage": { usePlanUsage: () => query },
  })
  let html = renderToStaticMarkup(React.createElement(mod.PostsAutomationPage))
  assert.match(html, /habilitado pelo plano, funcionalidade ainda indisponível/)
  assert.doesNotMatch(html, /type="checkbox"|role="switch"/)
  query = { ...query, data: plan("pro") }
  html = renderToStaticMarkup(React.createElement(mod.PostsAutomationPage))
  assert.match(html, /Recurso não incluído no seu plano atual/)
})

test("resumo é responsivo e não depende só de cor ou hover", async () => {
  const css = await readFile(new URL("../src/components/plans/planSummary.css", import.meta.url), "utf8")
  assert.match(css, /repeat\(auto-fit, minmax\(min\(100%, 200px\), 1fr\)\)/)
  assert.match(css, /flex-wrap: wrap/)
  assert.match(css, /focus-visible/)
  assert.match(css, /\.app-topbar \.plan-topbar-account \{[\s\S]*?flex-direction: column/)
  assert.match(css, /\.app-topbar \.plan-topbar-account \{[\s\S]*?padding-bottom: 24px/)
  assert.match(css, /\.plan-topbar-account \.active-profile-chip \{[\s\S]*?z-index: 2/)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag \{[\s\S]*?position: absolute/)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag \{[\s\S]*?left: 0;[\s\S]*?right: 0;[\s\S]*?bottom: 0/)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag \{[\s\S]*?z-index: 1/)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag > span \{[\s\S]*?width: 100%/)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag > span \{[\s\S]*?align-items: flex-end/)
  assert.match(css, /padding: 32px 12px 8px !important/)
  assert.doesNotMatch(css, /margin: 0 0 0 -19px/)
  const chip = await readFile(new URL("../src/components/profiles/ActiveProfileChip.tsx", import.meta.url), "utf8")
  assert.match(chip, /background: "#303440"/)
  assert.match(chip, /minHeight: 70/)
  assert.match(chip, /size=\{48\}/)
  assert.doesNotMatch(chip, /background: "rgba\(255,255,255,\.14\)"/)
  const panel = await readFile(new URL("../src/pages/PanelPage.tsx", import.meta.url), "utf8")
  assert.match(panel, /className="plan-topbar-account"[\s\S]*?<ActiveProfileChip \/>[\s\S]*?className="plan-topbar-tag"[\s\S]*?<PlanBadge \/>/)
  assert.match(panel, /const searchPage = searchPageForRoute\(location\.pathname, activeProductsTab\)/)
  assert.match(panel, /showSearch=\{searchPage !== null\}/)
  assert.match(panel, /onQuery=\{searchPage \? \(event\) => setPageSearch\(event\.target\.value\) : undefined\}/)
  assert.match(css, /min-height: var\(--hit-min\)/)
})
