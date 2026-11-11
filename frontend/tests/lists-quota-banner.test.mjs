import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const read = (file) => readFileSync(new URL(file, import.meta.url), "utf8")
const lists = read("../src/pages/ListasPage.tsx")
const products = read("../src/pages/ProductsPage.tsx")
const quota = read("../src/components/plans/ProductQuotaBar.tsx")

// Avalia a lógica de apresentação diretamente do componente, sem dependência do DOM.
const start = quota.indexOf("  const usage =")
const end = quota.indexOf("  return (", start)
assert.ok(start > 0 && end > start, "lógica de quota deve existir no componente")
const renderQuota = new Function("plan", "resource", "loading", "error",
  quota.slice(start, end) + "\nreturn {quota, canUpgrade, isLists}"
)

const usage = (used, limit, unlimited = false) => ({
  used, limit, unlimited, usage_status: "available",
})
const plan = (tier, listsUsage, admin = false) => ({
  plan_tier: tier, is_admin: admin,
  resources: { products: usage(6, 100), lists: listsUsage },
})

test("Listas usa a mesma barra compacta de Produtos sem resumo de plano", () => {
  assert.match(lists, /import \{ ResourceQuotaBar \} from "\.\.\/components\/plans\/ProductQuotaBar"/)
  assert.match(lists, /<ResourceQuotaBar\s+resource="lists"/)
  assert.match(lists, /plan=\{planQuery\.data\}/)
  assert.match(lists, /loading=\{planQuery\.isPending\}/)
  assert.match(lists, /error=\{planQuery\.isError\}/)
  assert.match(lists, /onUpgrade=\{\(\) => void router\.navigate\(\{ to: "\/planos", search: \{ de: "listas" \} \}\)\}/)
  assert.doesNotMatch(lists, /<PlanSummary|<PlanBadge|<UpgradeInfo/)
  assert.match(quota, /Cota de listas/)
  assert.doesNotMatch(quota, /Plano da conta|Sem cotas comerciais|Conhecer planos/)
})

test("Listas: Free/Pro têm contador e CTA, Premium apenas contador", () => {
  const free = renderQuota(plan("free", usage(4, 10)), "lists", false, false)
  assert.equal(free.quota, "4 de 10 utilizadas")
  assert.equal(free.canUpgrade, true)
  const pro = renderQuota(plan("pro", usage(8, 20)), "lists", false, false)
  assert.equal(pro.canUpgrade, true)
  const premium = renderQuota(plan("premium", usage(4, 100)), "lists", false, false)
  assert.equal(premium.quota, "4 de 100 utilizadas")
  assert.equal(premium.canUpgrade, false)
})

test("Listas: conta administrativa sem limite mostra uso sem upgrade", () => {
  const admin = renderQuota(plan("free", usage(4, null, true), true), "lists", false, false)
  assert.equal(admin.quota, "4 cadastradas · sem cota comercial")
  assert.equal(admin.canUpgrade, false)
  assert.equal(admin.isLists, true)
})

test("Estado de carregamento e ausência de quota são explícitos", () => {
  assert.equal(renderQuota(undefined, "lists", true, false).quota, "Consultando cota...")
  assert.equal(renderQuota(undefined, "lists", false, true).quota, "Cota indisponível")
  assert.equal(renderQuota(plan("free", {used:null, limit:10, unlimited:false, usage_status:"unavailable"}), "lists", false, false).quota, "Cota indisponível")
})

test("Produtos conserva comportamento e exportação anteriores", () => {
  assert.match(quota, /export const ProductQuotaBar = ResourceQuotaBar/)
  assert.match(products, /<ProductQuotaBar/)
  const product = renderQuota(plan("free", usage(4, 10)), "products", false, false)
  assert.equal(product.quota, "6 de 100 utilizados")
  assert.equal(product.isLists, false)
})
