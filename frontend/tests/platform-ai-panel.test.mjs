import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const file = (name) => readFileSync(new URL(name, import.meta.url), "utf8")

test("a página comum não exibe nenhum formulário de chave de IA, mesmo para ADMIN", () => {
  const page = file("../src/pages/CredentialsPage.tsx")
  assert.doesNotMatch(page, /AiCredentialCard|Inteligência Artificial|aiCredentialsApi/)
  assert.match(page, /groupCredentialCards/)
})

test("painel administrativo preserva gestão da IA e delega o teste ao botão geral", () => {
  const page = file("../src/pages/AdminCredentialsPage.tsx")
  const panel = file("../src/components/credentials/AdminAiCredentialCard.tsx")
  assert.match(page, /AdminAiCredentialCard/)
  for (const action of ["save", "delete", "activate"]) {
    assert.match(panel, new RegExp(`adminAiCredentialsApi\\.${action}\\(`))
  }
  assert.match(page, /testAllAdminConnections/)
  assert.doesNotMatch(panel, /adminAiCredentialsApi\.test\(/)
  assert.match(panel, /AI_PROVIDERS/)
  assert.match(panel, /Chave de API/)
  assert.match(panel, /Modelo \(opcional\)/)
})

test("geração e personalização não enviam clientes para Credenciais cadastrar chave", () => {
  const composer = file("../src/components/posts/PostComposer.tsx")
  const products = file("../src/pages/ProductsPage.tsx")
  assert.match(composer, /platformAiApi\.status/)
  assert.match(products, /platformAiApi\.status/)
  assert.doesNotMatch(products, /Cadastre sua chave Gemini em Credenciais/)
  assert.doesNotMatch(products, /provider: "gemini"/)
})
