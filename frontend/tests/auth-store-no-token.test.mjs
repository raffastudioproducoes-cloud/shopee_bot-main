import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const read = (rel) => readFile(new URL(rel, import.meta.url), "utf8")

test("authStore não guarda nem persiste token de acesso no navegador (S-06)", async () => {
  const store = await read("../src/stores/authStore.ts")
  // A única menção permitida é o migrate, que apaga o token deixado por versões antigas.
  const mentions = [...store.matchAll(/accessToken/g)]
  assert.equal(mentions.length, 1, "token só pode aparecer na limpeza de legado")
  assert.ok(store.indexOf("accessToken") > store.indexOf("migrate:"), "menção deve estar dentro do migrate")
  assert.match(store, /login: \(user: User\) => void/)
  assert.match(store, /partialize: \(state\) => \(\{\s*user: state\.user,\s*isAuthenticated: state\.isAuthenticated,\s*\}\)/)
  assert.match(store, /version: 1/)
  assert.match(store, /migrate:/)
})

test("nenhum chamador de login passa token", async () => {
  for (const rel of ["../src/router.tsx", "../src/pages/PanelPage.tsx", "../src/pages/LoginPage.tsx", "../src/pages/legal/LegalLayout.tsx"]) {
    const src = await read(rel)
    assert.doesNotMatch(src, /login\((?:""|\'\'),/, rel)
  }
})
