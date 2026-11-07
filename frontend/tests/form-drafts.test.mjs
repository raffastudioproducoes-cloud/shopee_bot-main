import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { createRequire } from "node:module"
import test from "node:test"

const require = createRequire(import.meta.url)
const ts = require("typescript")
const source = await readFile(new URL("../src/lib/formDraftStorage.ts", import.meta.url), "utf8")
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
const mod = { exports: {} }
new Function("module", "exports", compiled)(mod, mod.exports)
const { formDraftKey, saveFormDraft, readFormDraft, clearFormDraft } = mod.exports

function mockStorage() {
  const entries = new Map()
  globalThis.localStorage = {
    getItem: (key) => entries.get(key) ?? null,
    setItem: (key, value) => { entries.set(key, value) },
    removeItem: (key) => { entries.delete(key) },
  }
  return entries
}

test("recupera o rascunho, inclusive campos apagados de propósito", () => {
  mockStorage()
  const key = formDraftKey("cliente-1", "post-create", "perfil-1")
  assert.equal(saveFormDraft(key, { text: "Texto anterior", days: [1, 3] }), true)
  assert.deepEqual(readFormDraft(key), { text: "Texto anterior", days: [1, 3] })
  assert.equal(saveFormDraft(key, { text: "", days: [] }), true)
  assert.deepEqual(readFormDraft(key), { text: "", days: [] })
})

test("isola rascunhos por usuário, perfil e tipo de formulário", () => {
  mockStorage()
  const a = formDraftKey("conta-A", "post-create", "perfil-A")
  const b = formDraftKey("conta-B", "post-create", "perfil-A")
  const c = formDraftKey("conta-A", "post-create", "perfil-B")
  const d = formDraftKey("conta-A", "list-create", "perfil-A")
  for (const key of [a, b, c, d]) assert.ok(key)
  assert.equal(new Set([a, b, c, d]).size, 4)
  assert.equal(formDraftKey("conta-A", "post-create"), null)
  assert.ok(formDraftKey("conta-A", "product-create", null, false))
  saveFormDraft(a, { text: "privado" })
  for (const key of [b, c, d]) assert.equal(readFormDraft(key), null)
})

test("limpa após salvar com sucesso, mas nunca no simples fechamento", () => {
  mockStorage()
  const key = formDraftKey("cliente", "product-create", null, false)
  saveFormDraft(key, { name: "Produto ainda não enviado" })
  assert.deepEqual(readFormDraft(key), { name: "Produto ainda não enviado" })
  clearFormDraft(key)
  assert.equal(readFormDraft(key), null)
})

test("ignora e remove versões inválidas, dados corrompidos e rascunhos vencidos", () => {
  const entries = mockStorage()
  const key = formDraftKey("cliente", "list-create", "perfil")
  entries.set(key, "{corrompido")
  assert.equal(readFormDraft(key), null)
  entries.set(key, JSON.stringify({ version: 1, savedAt: Date.now() - 91 * 24 * 60 * 60 * 1000, value: { name: "antigo" } }))
  assert.equal(readFormDraft(key), null)
  assert.equal(entries.has(key), false)
  entries.set(key, JSON.stringify({ version: 2, savedAt: Date.now(), value: { name: "outro schema" } }))
  assert.equal(readFormDraft(key), null)
})

test("falhas de armazenamento e payload grande não impedem a edição", () => {
  mockStorage()
  const key = formDraftKey("cliente", "post-create", "perfil")
  assert.equal(saveFormDraft(key, { text: "x".repeat(300_000) }), false)
  globalThis.localStorage = {
    getItem: () => { throw new Error("storage bloqueado") },
    setItem: () => { throw new Error("quota") },
    removeItem: () => { throw new Error("blocked") },
  }
  assert.equal(readFormDraft(key), null)
  assert.equal(saveFormDraft(key, { text: "válido" }), false)
  assert.doesNotThrow(() => clearFormDraft(key))
})

test("contratos do hook e dos formulários não persistem File ou senha", async () => {
  const hook = await readFile(new URL("../src/hooks/useAutosavedDraft.ts", import.meta.url), "utf8")
  const posts = await readFile(new URL("../src/components/posts/PostComposer.tsx", import.meta.url), "utf8")
  const credentials = await readFile(new URL("../src/pages/CredentialsPage.tsx", import.meta.url), "utf8")
  const adminAi = await readFile(new URL("../src/components/credentials/AdminAiCredentialCard.tsx", import.meta.url), "utf8")
  const users = await readFile(new URL("../src/pages/UsersPage.tsx", import.meta.url), "utf8")
  assert.match(hook, /readyKey === key/)
  assert.match(posts, /pendingFileNames: pendingFiles\.map/)
  assert.match(posts, /setPendingFiles\(\[\]\)/)
  assert.match(users, /\{ username, access \}/)
  assert.doesNotMatch(users, /useAutosavedDraft\([^\n]+password/)
  assert.match(adminAi, /useAutosavedDraft\(draftKey, \{ provider, model \}/)
  assert.doesNotMatch(adminAi, /useAutosavedDraft\([^\n]+apiKey/)
  assert.match(credentials, /useAutosavedDraft\(publicIdDraftKey, \{ appId \}/)
  assert.doesNotMatch(credentials, /useAutosavedDraft\([^\n]+apiKey/)
  assert.doesNotMatch(credentials, /useAutosavedDraft\([^\n]+secret/)
})
