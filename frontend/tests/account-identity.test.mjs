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
  const { validCpf, formatCpf } = mod.exports
  assert.equal(validCpf("529.982.247-25"), true)
  assert.equal(validCpf("52998224725"), true)
  assert.equal(validCpf("111.111.111-11"), false)
  assert.equal(validCpf("52998224726"), false)
  assert.equal(formatCpf("52998224725"), "529.982.247-25")
  assert.equal(formatCpf("529.982.247-25"), "529.982.247-25")
  assert.equal(formatCpf("52998"), "529.98")
  assert.equal(formatCpf("529982247251234"), "529.982.247-25")
})

test("telefones aplicam máscaras por DDI e aceitam números brasileiros antigos", async () => {
  const transpiled = ts.transpileModule(await src("lib/phone.ts"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const mod = { exports: {} }
  vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
  const { PHONE_COUNTRIES, parseStoredPhone, internationalPhone, maskNationalPhone } = mod.exports
  const br = PHONE_COUNTRIES.find(country => country.id === "BR")
  const us = PHONE_COUNTRIES.find(country => country.id === "US")
  const pt = PHONE_COUNTRIES.find(country => country.id === "PT")
  assert.equal(parseStoredPhone("21999998888").country.id, "BR")
  assert.equal(parseStoredPhone("+5521999998888").national, "21999998888")
  assert.equal(parseStoredPhone("+351912345678").country.id, "PT")
  assert.equal(maskNationalPhone(br, "21999998888", true), "(21) 99999-8888")
  assert.equal(maskNationalPhone(br, "2199998888"), "(21) 9999-8888")
  assert.equal(maskNationalPhone(us, "4155551234"), "(415) 555-1234")
  assert.equal(maskNationalPhone(pt, "912345678"), "912 345 678")
  assert.equal(internationalPhone(pt, "912 345 678"), "+351912345678")
  assert.equal(internationalPhone(br, ""), "")
  assert.equal(internationalPhone(br, "219999988881234"), "+5521999998888")
  const form = await src("components/profiles/AccountIdentityForm.tsx")
  const phoneInput = await src("components/profiles/PhoneInput.tsx")
  assert.match(form, /<PhoneInput label="Celular \* para contratar plano" mobile/)
  assert.match(form, /<PhoneInput label="Telefone de contato \(opcional\)"/)
  assert.match(phoneInput, /<select[^>]*aria-label=\{`Código do país/)
  assert.match(phoneInput, /<input[^>]*type="tel"/)
})

test("Perfis mostra apenas cota compacta e cadastro por conta", async () => {
  const page = await src("pages/ProfilesPage.tsx")
  assert.doesNotMatch(page, /<PlanBadge \/>/)
  assert.match(page, /<ResourceQuotaBar[^>]*resource="profiles"/)
  assert.match(page, /<AccountIdentityForm \/>/)
  assert.doesNotMatch(page, /<PlanSummary|<UpgradeInfo/)
  const form = await src("components/profiles/AccountIdentityForm.tsx")
  for (const field of ["Nome e sobrenome", "CPF", "Celular", "Data de nascimento", "E-mail alternativo", "Telefone de contato", "Endereço", "CEP"]) {
    assert.match(form, new RegExp(field))
  }
  assert.match(form, /data\.purchase_readiness\.missing/)
  assert.match(form, /cpf_registered/)
  assert.match(form, /type="date"/)
  assert.match(form, /birth_date: form\.birth_date \|\| null/)
  assert.match(form, /formatCpf\(e\.target\.value\)/)
  assert.match(form, /export function AccountIdentityIntro\(\)/)
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
