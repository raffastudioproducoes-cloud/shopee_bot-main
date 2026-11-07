import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const src = (path) => readFile(new URL(`../src/${path}`, import.meta.url), "utf8")

test("campanha exibe caixas para todo catálogo social, inclusive planejadas, sem falsos cliques", async () => {
  const [picker, catalog, planner] = await Promise.all([
    src("components/campaigns/CampaignNetworkCheckboxes.tsx"),
    src("lib/credentialPlatforms.ts"),
    src("components/campaigns/CampaignPlanner.tsx"),
  ])
  assert.match(picker, /buildAdminDiagnosticSections\(\)\.social/)
  assert.match(catalog, /"shopee-video"/)
  assert.match(catalog, /"telegram"/)
  assert.match(catalog, /"whatsapp"/)
  assert.match(picker, /type="checkbox"/)
  assert.match(picker, /disabled=\{inputDisabled\}/)
  assert.match(picker, /state\?\.connected === true/)
  assert.match(picker, /isNetworkDisabled\(key\)/)
  assert.match(picker, /!event\.currentTarget\.checked/)
  assert.match(planner, /scope="campaign"/)
  assert.match(planner, /scope=\{`campaign-product-\$\{id\}`\}/)
  assert.match(planner, /setCampaignNetworkForAll/)
  assert.doesNotMatch(picker, /onClick=\{\(\) => onToggle/)
})

test("estado de credenciais é isolado por perfil ativo", async () => {
  const page = await src("pages/CreatePostPage.tsx")
  assert.match(page, /queryKey: \["credentials", activeProfileId\]/)
  assert.match(page, /enabled: Boolean\(activeProfileId\)/)
})
