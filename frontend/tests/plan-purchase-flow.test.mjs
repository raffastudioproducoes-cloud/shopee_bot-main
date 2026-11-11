import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"
import ts from "typescript"

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), "utf8")

function loadIntent() {
  const { outputText } = ts.transpileModule(read("lib/planIntent.ts"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } })
  const module = { exports: {} }
  new Function("module", "exports", outputText)(module, module.exports)
  return module.exports
}

test("planIntent só deixa passar planos, períodos, retornos e origens conhecidos", () => {
  const { parsePlanIntent, parsePlanosSearch } = loadIntent()
  assert.deepEqual({ ...parsePlanIntent({ plano: "pro", periodo: "yearly" }) }, { plano: "pro", periodo: "yearly" })
  assert.deepEqual({ ...parsePlanIntent({ plano: "free", periodo: "9m" }) }, {})
  assert.deepEqual({ ...parsePlanIntent({ plano: "https://evil.example", periodo: ["yearly"] }) }, {})
  assert.deepEqual({ ...parsePlanosSearch({ assinatura: "sucesso", de: "produtos" }) }, { assinatura: "sucesso", de: "produtos" })
  assert.deepEqual({ ...parsePlanosSearch({ assinatura: "pago", de: "../x" }) }, {})
  assert.deepEqual({ ...parsePlanosSearch({ de: "a".repeat(40) }) }, {})
})

test("todos os botões de upgrade levam à tela /planos", () => {
  for (const [file, de] of [["ProductsPage", "produtos"], ["ListasPage", "listas"], ["ProfilesPage", "perfis"], ["CreatePostPage", "publicacao"]]) {
    const source = read(`pages/${file}.tsx`)
    assert.match(source, new RegExp(`to: "/planos", search: \\{ de: "${de}" \\}`), `${file} sem destino /planos`)
    assert.doesNotMatch(source, /hash: "planos"/)
  }
  const summary = read("components/plans/PlanSummary.tsx")
  assert.match(summary, /Ver planos e assinar/)
  assert.match(summary, /to="\/planos"/)
  assert.doesNotMatch(summary, /ainda não estão disponíveis|Não há cobrança/)
})

test("o selo de plano do topo e o menu lateral abrem os planos", () => {
  assert.match(read("components/plans/PlanSummary.tsx"), /className="plan-badge-link"/)
  assert.match(read("pages/PanelPage.tsx"), /value: '\/planos', label: 'Planos'/)
  const router = read("router.tsx")
  assert.match(router, /path: "\/planos",\s+validateSearch/)
})

test("a apresentação leva Pro e Premium ao login com o plano e o período escolhidos", () => {
  const offer = read("pages/presentation/Offer.tsx")
  assert.match(offer, /to="\/login" search=\{\{ plano: offer\.id, periodo: period \}\}/)
  assert.match(offer, /to="\/planos" search=\{\{ plano: offer\.id, periodo: period \}\}/)
  assert.match(offer, /prices\.data\?\.checkout_enabled === true/)
  // sem a contratação liberada no servidor, continua o botão Entrar de antes
  assert.match(offer, /offer\.id === "free" \? "Começar grátis" : "Entrar"/)
})

test("o login valida a intenção antes de abrir o pagamento e a guarda só em sessionStorage", () => {
  const login = read("pages/LoginPage.tsx")
  assert.match(login, /parsePlanIntent\(/)
  assert.match(login, /navigate\(\{ to: '\/planos', search: intent \}\)/)
  assert.doesNotMatch(login, /localStorage/)
  assert.match(read("router.tsx"), /path: "\/login",\s+\/\/[^\n]*\n\s+validateSearch/)
})

test("fatura só vira link se for do Asaas em https", async () => {
  const card = read("components/plans/SubscriptionCard.tsx")
  assert.match(card, /u\.protocol === "https:"/)
  assert.match(card, /hostname === "asaas\.com" \|\| u\.hostname\.endsWith\("\.asaas\.com"\)/)
  assert.match(card, /rel="noopener noreferrer"/)
  assert.doesNotMatch(card, /dangerouslySetInnerHTML/)
})

test("cancelar pede confirmação e explica que o plano vale até o fim do período pago", () => {
  const card = read("components/plans/SubscriptionCard.tsx")
  assert.match(card, /role="alertdialog"/)
  assert.match(card, /Seu plano continua até/)
  assert.match(card, /Sim, cancelar/)
})
