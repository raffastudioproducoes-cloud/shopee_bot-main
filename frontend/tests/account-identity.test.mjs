import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import vm from "node:vm"
import ts from "typescript"

const src = (name) => readFile(new URL(`../src/${name}`, import.meta.url), "utf8")

test("CPF só aceita documento com dígitos verificadores válidos", async () => {
  const transpiled = ts.transpileModule(await src("lib/cpf.ts"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const mod = { exports: {} }
  vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
  const { validCpf } = mod.exports
  assert.equal(validCpf("529.982.247-25"), true)
  assert.equal(validCpf("52998224725"), true)
  assert.equal(validCpf("111.111.111-11"), false)
  assert.equal(validCpf("52998224726"), false)
})

test("Perfis mostra apenas cota compacta e cadastro por conta", async () => {
  const page = await src("pages/ProfilesPage.tsx")
  assert.doesNotMatch(page, /<PlanBadge \/>/)
  assert.match(page, /<ResourceQuotaBar[^>]*resource="profiles"/)
  assert.match(page, /<AccountIdentityForm \/>/)
  assert.doesNotMatch(page, /<PlanSummary|<UpgradeInfo/)
  const form = await src("components/profiles/AccountIdentityForm.tsx")
  for (const field of ["Nome e sobrenome", "CPF", "Celular", "Idade", "E-mail alternativo", "Telefone de contato", "Endereço", "CEP"]) {
    assert.match(form, new RegExp(field))
  }
  assert.match(form, /data\.purchase_readiness\.missing/)
  assert.match(form, /cpf_registered/)
  assert.match(form, /<form onSubmit=\{handleSubmit\}>/)
  assert.match(form, /<fieldset className="account-identity__fieldset" disabled=\{!data\}>/)
  assert.doesNotMatch(form, /\{data && <form/)
  assert.match(form, /disabled=\{!data \|\| save\.isPending/)
  assert.doesNotMatch(form, /localStorage|sessionStorage/)
})

test("cadastro exige nome completo, CPF, e-mail e senha sem nome de usuário manual", async () => {
  const page = await src("pages/LoginPage.tsx")
  const auth = await src("api/auth.ts")
  assert.match(page, /authApi\.register\(fullName, cpf, email, password, confirmPassword\)/)
  assert.match(page, /label="Nome completo \*"/)
  assert.match(page, /label="CPF \*"/)
  assert.match(auth, /full_name: fullName, cpf, email, password/)
  assert.match(page, /authApi\.completeGoogle\(fullName, cpf\)/)
})
