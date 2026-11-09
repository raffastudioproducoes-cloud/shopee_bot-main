import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const src = (path) => readFile(new URL(`../src/${path}`, import.meta.url), "utf8")

test("Publicação única e campanha compartilham a lista compacta das nove redes", async () => {
  const [picker, catalog, planner, composer, css] = await Promise.all([
    src("components/posts/NetworkPicker.tsx"),
    src("lib/credentialPlatforms.ts"),
    src("components/campaigns/CampaignPlanner.tsx"),
    src("components/posts/PostComposer.tsx"),
    src("components/posts/NetworkPicker.css"),
  ])
  assert.match(picker, /buildAdminDiagnosticSections\(\)\.social/)
  assert.match(catalog, /"shopee-video"/)
  assert.match(catalog, /"telegram"/)
  assert.match(catalog, /"whatsapp"/)
  assert.match(picker, /type="checkbox"/)
  assert.match(picker, /disabled=\{disabled\}/)
  assert.match(picker, /state\?\.connected === true/)
  assert.match(picker, /isNetworkDisabled\(key\)/)
  assert.match(picker, /!event\.currentTarget\.checked/)
  assert.match(planner, /<NetworkPicker selected=\{draft\.networks\}/)
  assert.equal((planner.match(/<NetworkPicker selected=/g) ?? []).length, 1)
  assert.doesNotMatch(planner, /<NetworkPicker selected=\{snapshot\.networks\}/)
  assert.match(planner, /networks: draft\.networks/)
  assert.match(planner, /campaign-description-tabs/)
  assert.ok(planner.indexOf('className="campaign-textarea"') < planner.indexOf("campaign-description-tabs"))
  assert.ok(planner.indexOf("campaign-description-tabs") < planner.indexOf("campaign-ai-controls"))
  assert.match(planner, /snapshot\.networkCopies\[activeNetwork\] \|\| snapshot\.copy/)
  assert.match(planner, /snapshot\.affiliateLink/)
  assert.match(planner, /textLength\(NETWORK_RULES\[activeNetwork\], finalText\)/)
  assert.match(planner, /slice\(productPageStart, productPageStart \+ 10\)/)
  assert.match(composer, /<NetworkPicker selected=\{activeNetworks\}/)
  assert.match(composer, /readOnly=\{!!post\}/)
  assert.match(picker, /Boolean\(readOnly\)/)
  assert.doesNotMatch(planner, /campaignNetworkSelection|updateAllNetworks/)
  assert.doesNotMatch(picker.split("interface LimitsPanelProps")[0], /<NetworkLogo|<img\b|<button\b/)
  assert.match(css, /\.compact-network-option\s*\{/)
  assert.doesNotMatch(css, /background:|border:/)
})

test("estado de credenciais é isolado por perfil ativo", async () => {
  const page = await src("pages/CreatePostPage.tsx")
  assert.match(page, /queryKey: \["credentials", userId, activeProfileId\]/)
  assert.match(page, /enabled: Boolean\(userId && activeProfileId\)/)
})


test("campanha mostra a composição aceita e as mídias descartadas por rede", async () => {
  const [selector, planner] = await Promise.all([
    src("components/campaigns/CampaignProductMediaSelector.tsx"),
    src("components/campaigns/CampaignPlanner.tsx"),
  ])
  assert.match(selector, /planMediaComposition/)
  assert.match(selector, /legacyMedia/)
  assert.match(selector, /plan\.dropped\.map/)
  assert.match(selector, /plan\.blockedReason/)
  assert.match(selector, /aria-live="polite"/)
  assert.match(selector, /affiliateLink && !body\.includes/)
  assert.match(selector, /video\.duration/)
  assert.match(selector, /image\.naturalWidth/)
  assert.match(selector, /metadataPending/)
  assert.match(planner, /legacyMedia=\{mediaQuery\.data\?\.data\.filter/)
  assert.match(planner, /texts=\{Object\.fromEntries/)
})

test("planejador de composição é compartilhado e bloqueia texto fora do limite", async () => {
  const [composition, limits, backend] = await Promise.all([
    src("lib/mediaComposition.ts"),
    src("lib/networkLimits.ts"),
    readFile(new URL("../../api/media_composition.py", import.meta.url), "utf8"),
  ])
  assert.match(composition, /adaptMedia\(rule, draft\.media\)/)
  assert.match(composition, /TEXT_ERROR_KEYS/)
  assert.match(composition, /mode: "blocked"/)
  assert.match(composition, /blockedReason/)
  assert.match(limits, /if \(len > rule\.maxChars\)/)
  assert.match(backend, /plan_network_composition/)
  assert.match(backend, /Text errors still block/)
})
