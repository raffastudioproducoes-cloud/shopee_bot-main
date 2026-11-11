import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const src = readFileSync(new URL("../src/components/plans/PlanCheckout.tsx", import.meta.url), "utf8")
const comparison = readFileSync(new URL("../src/components/plans/PlanComparison.tsx", import.meta.url), "utf8")
const api = readFileSync(new URL("../src/api/billing.ts", import.meta.url), "utf8")

test("os quatro períodos aprovados aparecem, sem 9 meses", () => {
  for (const label of ["Mensal", "3 meses", "6 meses", "1 ano"]) assert.match(src, new RegExp(`"${label}"`))
  assert.doesNotMatch(src, /9 meses/)
})

test("preço vem do servidor e o pagamento sai para o Asaas", () => {
  assert.match(api, /"\/billing\/plans"/)
  assert.match(api, /"\/billing\/checkout"/)
  assert.match(src, /window\.location\.assign\(data\.checkout_url\)/)
  assert.doesNotMatch(src, /5990|10990|59,90|109,90/)
})

test("cartão e Pix são oferecidos e o retorno não confirma pagamento", () => {
  assert.match(src, /"CREDIT_CARD"/)
  assert.match(src, /"PIX"/)
  assert.match(src, /assim que o Asaas confirmar/)
})

test("ADMIN não vê o checkout e o texto antigo de indisponível saiu", () => {
  assert.match(comparison, /data\?\.is_admin \?/)
  assert.doesNotMatch(comparison, /ainda não estão disponíveis/)
})
