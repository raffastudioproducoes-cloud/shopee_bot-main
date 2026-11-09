import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const read = (path) => readFile(new URL("../" + path, import.meta.url), "utf8")
const dir = "src/pages/presentation/"

test("apresentação tem todas as seções e âncoras do menu", async () => {
  const sources = (await Promise.all(["Hero", "Scenes", "Sections", "Plans", "Offer"].map((n) => read(`${dir}${n}.tsx`)))).join("\n")
  for (const id of ["desafio", "acumulo", "virada", "como-funciona", "beneficios", "recursos", "perguntas", "planos", "valores", "comecar"]) {
    assert.ok(sources.includes(`id="${id}"`), `falta a seção ${id}`)
  }
  const body = await read(`${dir}PresentationBody.tsx`)
  for (const href of ["#desafio", "#como-funciona", "#recursos", "#planos", "#valores", "#perguntas"]) {
    assert.ok(body.includes(`href="${href}"`), `menu sem ${href}`)
  }
  for (const section of ["Hero", "ChallengeScene", "BacklogScene", "TurnScene", "ProductScene", "BenefitsSection", "FutureSection", "TrustSection", "PlansScene", "OfferSection", "FinalSection"]) {
    assert.ok(body.includes(`<${section} />`), `página não renderiza ${section}`)
  }
})

test("rodapé mantém Termos e Privacidade e todos os botões Entrar vão para /login no app", async () => {
  const body = await read(`${dir}PresentationBody.tsx`)
  assert.match(body, /href="\/termos"/)
  assert.match(body, /href="\/privacidade"/)
  const content = await read(`${dir}content.ts`)
  assert.match(content, /LOGIN_PATH = "\/login"/)
  for (const f of ["Hero", "Sections", "Offer", "PresentationBody"]) {
    const src = await read(`${dir}${f}.tsx`)
    assert.doesNotMatch(src, /onrender\.com/, `${f} aponta para URL externa`)
  }
})

test("movimento respeita 'reduzir movimento' e a página é carregada sob demanda", async () => {
  const body = await read(`${dir}PresentationBody.tsx`)
  assert.match(body, /<MotionConfig reducedMotion="user">/)
  const shared = await read(`${dir}shared.tsx`)
  assert.match(shared, /useReducedMotion\(\)/)
  const page = await read("src/pages/PresentationPage.tsx")
  assert.match(page, /lazy\(\(\) => import\("\.\/presentation\/PresentationBody"\)\)/)
})

test("limites dos planos são os da migração 072 e os preços são os informados por Rafa", async () => {
  const sql = await read("../database/migrations/072_plan_limits_and_atomic_catalog_quotas.sql")
  const rows = Object.fromEntries(
    [...sql.matchAll(/\('(free|pro|premium)',(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(true|false)\)/g)]
      .map((m) => [m[1], m.slice(2).map((v) => (v === "true" ? true : v === "false" ? false : Number(v)))]),
  )
  assert.deepEqual(Object.keys(rows).sort(), ["free", "premium", "pro"])
  const content = await read(`${dir}content.ts`)
  const plan = (id) => content.match(new RegExp(`\\{ id: "${id}", name:[^\\n]*`))?.[0] ?? ""
  for (const [id, r] of Object.entries(rows)) {
    const [products, lists, perHour, slots, activeCampaigns, days, postsPerDay, profiles, automation] = r
    const line = plan(id)
    assert.ok(line.includes(`products: ${products},`), `${id}: produtos`)
    assert.ok(line.includes(`lists: ${lists},`), `${id}: listas`)
    assert.ok(line.includes(`profiles: ${profiles},`), `${id}: perfis`)
    assert.ok(line.includes(`postsPerHour: ${perHour},`), `${id}: envios por hora`)
    assert.ok(line.includes(`recurringSlots: ${slots},`), `${id}: horários recorrentes`)
    assert.ok(line.includes(`automation: ${automation}`), `${id}: automação`)
    if (days === 0) assert.ok(line.includes("campaign: null"), `${id}: campanha`)
    else assert.ok(line.includes(`campaign: { maxDays: ${days}, postsPerDay: ${postsPerDay}, active: ${activeCampaigns} }`), `${id}: campanha`)
  }
  // Valores de referência informados por Rafa em 09/11/2026: Pro R$ 59,90 e Premium R$ 109,90 por mês.
  const prices = [...content.matchAll(/R\$\s?\d+(?:,\d{2})?/g)].map((m) => m[0])
  assert.deepEqual(prices.sort(), ["R$ 109,90", "R$ 59,90"], "só os dois valores informados podem aparecer")
  assert.match(content, /id: "pro", priceLabel: "R\$ 59,90"/)
  assert.match(content, /id: "premium", priceLabel: "R\$ 109,90"/)
  assert.match(content, /id: "free", priceLabel: "Grátis"/)
})

test('produtos reais de exemplo: dados estáticos, sem link de afiliado, preço só formatado em tela e reserva de imagem', async () => {
  const demo = await read(`${dir}demoProducts.ts`)
  assert.ok((demo.match(/image: `\$\{CDN\}/g) ?? []).length >= 8, 'pelo menos 8 produtos reais')
  assert.doesNotMatch(demo, /shope\.ee|s\.shopee\.com|affiliate|commission|original_link/i, 'sem link de afiliado nem comissão')
  assert.doesNotMatch(demo, /\bR\$\s?\d/, 'preço guardado como número; o formato vem de toLocaleString')
  assert.match(demo, /const CDN = "https:\/\/cf\.shopee\.com\.br\/file\/"/)
  const shared = await read(`${dir}shared.tsx`)
  assert.match(shared, /onError=\{\(\) => setFailed\(true\)\}/)
  assert.match(shared, /referrerPolicy="no-referrer"/)
  for (const f of ['Hero', 'Scenes', 'ProductDemo']) {
    const src = await read(`${dir}${f}.tsx`)
    assert.match(src, /demoProducts|ProductThumb/, `${f} usa os produtos de exemplo`)
  }
  const scenes = await read(`${dir}Scenes.tsx`)
  assert.match(scenes, /produtos reais de um catálogo de exemplo/, 'rótulo honesto: exemplo e status ilustrativos')
  assert.doesNotMatch(scenes, /sem dados reais/)
})

test('tabela de planos da apresentação destaca só o Pro (selo e faixa), como a tabela das configurações', async () => {
  const offer = await read(`${dir}Offer.tsx`)
  assert.equal((offer.match(/Recomendado/g) ?? []).length, 1)
  assert.match(offer, /highlight=\{plan\.id === "pro"\}/)
  assert.match(offer, /<PlanTag tier=\{plan\.id\}>\{plan\.name\}<\/PlanTag>/)
})
