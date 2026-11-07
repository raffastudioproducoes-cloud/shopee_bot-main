import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const sectionsModule = await (async () => {
  try {
    return await import("../src/lib/credentialSections.ts")
  } catch (error) {
    if (error?.code !== "ERR_UNKNOWN_FILE_EXTENSION") throw error
    // CI Node 20: transpilar com a dependência TypeScript já existente.
    const ts = await import("typescript")
    const source = readFileSync(new URL("../src/lib/credentialSections.ts", import.meta.url), "utf8")
    const { outputText } = ts.transpileModule(source, {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
    })
    return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
  }
})()

const { groupCredentialCards } = sectionsModule

test("conectadas em cima, pendentes embaixo, ambas em ordem alfabética PT-BR", () => {
  const cards = [
    { title: "Threads", connected: true },
    { title: "X (Twitter)", connected: false },
    { title: "Shopee", connected: true, light: "yellow", state: "stale" },
    { title: "Facebook", connected: false },
    { title: "Inteligência Artificial", connected: true },
    { title: "Árvore", connected: false },
  ]
  const result = groupCredentialCards(cards)
  assert.deepEqual(result.registered.map((x) => x.title), ["Inteligência Artificial", "Shopee", "Threads"])
  assert.deepEqual(result.pending.map((x) => x.title), ["Árvore", "Facebook", "X (Twitter)"])
  assert.equal(result.registered.find((x) => x.title === "Shopee").state, "stale")
  assert.equal(cards[0].title, "Threads", "não mutar entrada original")
})

test("ao conectar/desconectar, o card troca de grupo sem duplicação", () => {
  const cards = [{ title: "Shopee", connected: false }, { title: "Threads", connected: true }]
  assert.deepEqual(groupCredentialCards(cards).registered.map(x => x.title), ["Threads"])
  const connected = cards.map(x => x.title === "Shopee" ? { ...x, connected: true } : x)
  assert.deepEqual(groupCredentialCards(connected).registered.map(x => x.title), ["Shopee", "Threads"])
  const disconnected = connected.map(x => x.title === "Threads" ? { ...x, connected: false } : x)
  assert.deepEqual(groupCredentialCards(disconnected).pending.map(x => x.title), ["Threads"])
})

test("seções sem itens e ordenação não dependem de luz/validade do teste", () => {
  assert.deepEqual(groupCredentialCards([]), { registered: [], pending: [] })
  const result = groupCredentialCards([{ title: "Shopee Vídeo", connected: false, light: "yellow" }])
  assert.equal(result.registered.length, 0)
  assert.deepEqual(result.pending.map(x => x.title), ["Shopee Vídeo"])
})

test("página comum não consulta nem classifica chave de IA da plataforma", () => {
  const page = readFileSync(new URL("../src/pages/CredentialsPage.tsx", import.meta.url), "utf8")
  assert.doesNotMatch(page, /aiCredentialsApi|AiCredentialCard|queryKey: \["credentials", "ai"\]/)
  assert.match(page, /if \(isLoading\)/)
  assert.match(page, /Não foi possível consultar o cadastro das credenciais/)
  assert.match(page, /connected: Boolean\(status\?\.shopee\?\.connected\)|\.\.\.SIMPLE_NETWORKS\.map/)
  assert.match(page, /connected: Boolean\(shopeeVideoStatus\?\.connected\)/)
  assert.match(page, /shopeeVideoApi\.status/)
  assert.match(page, /publicação de vídeos[^]*?indisponível/)
})
