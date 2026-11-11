import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), "utf8")
const checkout = read("components/plans/PlanCheckout.tsx")
const intent = read("lib/planIntent.ts")
const api = read("api/billing.ts")

test("os quatro períodos aprovados existem, sem 9 meses", () => {
  for (const label of ["Mensal", "3 meses", "6 meses", "1 ano"]) assert.match(intent, new RegExp(`"${label}"`))
  assert.doesNotMatch(intent + checkout, /9 meses/)
})

test("preço vem do servidor e o pagamento sai para o Asaas", () => {
  assert.match(api, /"\/billing\/plans"/)
  assert.match(api, /"\/billing\/checkout"/)
  assert.match(checkout, /window\.location\.assign\(data\.checkout_url\)/)
  assert.doesNotMatch(checkout, /5990|10990|59,90|109,90/)
})

test("cartão e Pix, resumo antes de pagar e aviso de confirmação pelo Asaas", () => {
  assert.match(checkout, /"CREDIT_CARD"/)
  assert.match(checkout, /"PIX"/)
  assert.match(checkout, /<h3>Resumo<\/h3>/)
  assert.match(checkout, /quando o Asaas confirma o pagamento/)
  assert.match(checkout, /to="\/termos"/)
})

test("contratação fica bloqueada sem o servidor liberar, no mesmo plano ou com assinatura aberta", () => {
  assert.match(checkout, /prices\.data\?\.checkout_enabled === true/)
  assert.match(checkout, /const blocked = !enabled \|\| !selected \|\| alreadyThis \|\| hasSubscription/)
})

test("a tela de planos é do cliente: ADMIN não contrata e o painel ADMIN não vem junto", () => {
  const page = read("pages/PlanosPage.tsx")
  assert.match(page, /plan\?\.is_admin/)
  assert.doesNotMatch(page + checkout, /billingAdmin|BillingAdminPanel|\/admin\/billing/)
  assert.doesNotMatch(api.replace(/^\/\/.*$/gm, ""), /billingAdmin|\/admin\/billing/)
})

test("Planos mostra cancelamento sempre, guia de teste só no sandbox e a tabela de limites", () => {
  const card = readFileSync(new URL("../src/components/plans/SubscriptionCard.tsx", import.meta.url), "utf8")
  assert.match(card, /Cancelamento de plano/)
  assert.match(card, /Cancelar plano/)
  assert.match(card, /paidAccount/)
  const page = readFileSync(new URL("../src/pages/PlanosPage.tsx", import.meta.url), "utf8")
  assert.match(page, /prices\.data\?\.sandbox && prices\.data\.checkout_enabled && <SandboxGuide \/>/)
  assert.match(page, /<SubscriptionCard tier=\{tier\} \/>/)
  const guide = readFileSync(new URL("../src/components/plans/SandboxGuide.tsx", import.meta.url), "utf8")
  assert.match(guide, /4539 6560 4839 2220/)
  assert.match(guide, /nada é cobrado de verdade/)
})

test("plano pago sem assinatura também pode ser cancelado (volta ao Free) e atualiza os limites", () => {
  const card = readFileSync(new URL("../src/components/plans/SubscriptionCard.tsx", import.meta.url), "utf8")
  assert.match(card, /const unbilled = !sub && paidAccount/)
  assert.match(card, /unbilled && !confirming/)
  assert.match(card, /invalidateQueries\(\{ queryKey: \["plan-usage"\] \}\)/)
  assert.doesNotMatch(card, /<Button variant="ghost" disabled>Cancelar plano<\/Button>/)
})
