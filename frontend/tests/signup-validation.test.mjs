import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"
import { buildSync } from "esbuild"

const entry = new URL("../src/lib/identityValidation.ts", import.meta.url).pathname
const { outputFiles } = buildSync({ entryPoints: [entry], bundle: true, format: "cjs", write: false })
const mod = { exports: {} }
new Function("module", "exports", outputFiles[0].text)(mod, mod.exports)
const v = mod.exports
const login = readFileSync(new URL("../src/pages/LoginPage.tsx", import.meta.url), "utf8")

test("CPF: dígitos faltando, repetidos e verificador errado são recusados; válido passa", () => {
  assert.equal(v.cpfProblem(""), null)
  assert.match(v.cpfProblem("529.982"), /Faltam 5 dígito/)
  assert.match(v.cpfProblem("000.000.000-00"), /inválido/)
  assert.match(v.cpfProblem("111.111.111-11"), /inválido/)
  assert.match(v.cpfProblem("529.982.247-26"), /inválido/)
  assert.equal(v.cpfProblem("529.982.247-25"), null)
})

test("e-mail: exige @, domínio com ponto e TLD de letras", () => {
  for (const bad of ["rafacelle27", "a@b", "a@b.c", "a@b.12", "a b@exemplo.com", "a@@exemplo.com", "@exemplo.com"]) {
    assert.equal(v.validEmail(bad), false, bad)
  }
  for (const ok of ["cliente@example.com", "nome.sobrenome@mail.exemplo.com.br"]) assert.equal(v.validEmail(ok), true, ok)
  assert.match(v.emailProblem("rafacelle27"), /e-mail válido/)
})

test("nome: sobrenome obrigatório, sem números", () => {
  assert.match(v.fullNameProblem("Rafael"), /sobrenome/)
  assert.match(v.fullNameProblem("Rafael 2"), /números/)
  assert.equal(v.fullNameProblem("Rafael Silva"), null)
})

test("senha: mínimo visível e validado", () => {
  assert.match(v.PASSWORD_HINT, /Mínimo de 8 caracteres/)
  assert.match(v.passwordProblem("1234567"), /ao menos 8/)
  assert.equal(v.passwordProblem("12345678"), null)
})

test("cadastro usa máscara de CPF, mensagens por campo e só libera o botão com tudo válido", () => {
  assert.match(login, /onChange=\{e => setCpf\(formatCpf\(e\.target\.value\)\)\}/)
  assert.match(login, /error=\{cpfError\}/)
  assert.match(login, /error=\{emailError\}/)
  assert.match(login, /hint=\{PASSWORD_HINT\}/)
  assert.match(login, /error=\{confirmError\}/)
  assert.match(login, /!enabled \|\| !formValid/)
})
