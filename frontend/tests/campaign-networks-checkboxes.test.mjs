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
  assert.match(planner, /<NetworkPicker selected=\{snapshot\.networks\}/)
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
