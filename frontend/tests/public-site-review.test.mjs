import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

// Requisitos das revisões de app (TikTok/Meta) que dependem do site público.
const read = (path) => readFile(new URL("../" + path, import.meta.url), "utf8")

test("landing explica o app em PT e EN, com permissões por rede e sem uso interno", async () => {
  const info = await read("src/pages/presentation/AppInfoSection.tsx")
  for (const scope of ["instagram_basic", "instagram_content_publish", "instagram_manage_insights", "pages_show_list",
    "pages_read_engagement", "pages_manage_posts", "read_insights", "threads_basic", "threads_content_publish",
    "threads_manage_insights", "user.info.basic", "video.publish", "tweet.write"]) {
    assert.ok(info.includes(scope), `falta o escopo ${scope}`)
  }
  assert.match(info, /pt: \{/)
  assert.match(info, /en: \{/)
  assert.match(info, /not an internal or personal-use tool/)
  assert.match(info, /Não é uma ferramenta interna/)
  assert.match(info, /contato\.raffasp@gmail\.com/)
  const body = await read("src/pages/presentation/PresentationBody.tsx")
  assert.ok(body.includes("<AppInfoSection lang={lang} first />"), "em inglês a explicação vem antes da apresentação")
  assert.ok(body.includes("<Hero /><AppInfoSection lang={lang} />"), "em português a explicação vem logo após o Hero")
  assert.doesNotMatch(body, /noindex/, "a landing pública precisa ser indexável (staging segue noindex pelo servidor)")
})

test("links legais ficam visíveis no cabeçalho e no rodapé da landing, sem abrir menu", async () => {
  const body = await read("src/pages/presentation/PresentationBody.tsx")
  const header = body.slice(body.indexOf("<header"), body.indexOf("</header>"))
  assert.match(header, /links\.map/)
  assert.doesNotMatch(header.slice(header.indexOf("Links legais")), /hidden/, "linha legal não pode ser escondida no celular")
  const footer = body.slice(body.indexOf("<footer"), body.indexOf("</footer>"))
  assert.match(footer, /href="\/termos"/)
  assert.match(footer, /href="\/privacidade"/)
  assert.match(footer, /links\.slice\(2\)/)
  const info = await read("src/pages/presentation/AppInfoSection.tsx")
  for (const href of ["/termos", "/privacidade", "/exclusao-de-dados", "/dados-coletados", "mailto:"]) {
    assert.ok(info.includes(href), `legalLinks sem ${href}`)
  }
})

test("páginas legais e exclusão de dados são públicas e têm versão em inglês completa", async () => {
  const router = await read("src/router.tsx")
  for (const path of ["/termos", "/privacidade", "/dados-coletados", "/exclusao-de-dados"]) {
    const route = router.match(new RegExp(`createRoute\\(\\{\\s*getParentRoute: \\(\\) => rootRoute,\\s*path: ["']${path}["']`))
    assert.ok(route, `${path} precisa ser rota pública (filha da raiz, fora do painel)`)
  }
  const terms = await read("src/pages/legal/TermsEn.tsx")
  const privacy = await read("src/pages/legal/PrivacyPolicyEn.tsx")
  assert.ok((terms.match(/<h2>/g) ?? []).length >= 12, "termos em inglês completos")
  assert.ok((privacy.match(/<h2>/g) ?? []).length >= 12, "privacidade em inglês completa")
  for (const word of ["Meta", "TikTok", "X", "Asaas", "Supabase", "Render", "Fernet", "GDPR", "LGPD", "/api/meta/data-deletion"]) {
    assert.ok(privacy.includes(word), `privacidade EN sem ${word}`)
  }
  const pt = await read("src/pages/legal/PrivacyPolicyPage.tsx")
  assert.doesNotMatch(pt, /legal-placeholder|completar:/, "sem marcador de rascunho visível ao revisor")
  assert.match(pt, /Asaas/)
  const deletion = await read("src/pages/legal/DataDeletionPage.tsx")
  assert.match(deletion, /function DataDeletionPt/)
  assert.match(deletion, /function DataDeletionEn/)
  assert.match(deletion, /contato\.raffasp@gmail\.com/)
})

test("idioma vem de ?lang=, da escolha salva ou do navegador", async () => {
  const lang = await read("src/lib/siteLang.ts")
  assert.match(lang, /get\("lang"\)/)
  assert.match(lang, /startsWith\("pt"\) \? "pt" : "en"/)
  assert.match(lang, /try \{ window\.localStorage/)
})

test("robots aponta o sitemap e o sitemap só lista páginas públicas", async () => {
  const robots = await read("public/robots.txt")
  assert.match(robots, /^Sitemap: https:\/\/shopee-bot-fj0w\.onrender\.com\/sitemap\.xml$/m)
  const sitemap = await read("public/sitemap.xml")
  const locs = [...sitemap.matchAll(/<loc>https:\/\/shopee-bot-fj0w\.onrender\.com([^<]*)<\/loc>/g)].map((m) => m[1])
  assert.deepEqual(locs.sort(), ["/", "/dados-coletados", "/exclusao-de-dados", "/privacidade", "/termos"])
  for (const path of locs.filter((p) => p !== "/")) assert.doesNotMatch(robots, new RegExp(`Disallow: ${path}$`, "m"))
})
