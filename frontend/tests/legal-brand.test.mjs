import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('Termos de Uso usa Auto Orbital e não mais ShopeeAutoVendas', () => {
  const terms = source('../src/pages/legal/TermsPage.tsx')
  assert.match(terms, /Auto Orbital/)
  assert.doesNotMatch(terms, /ShopeeAutoVendas/)
})

test('Política de Privacidade tem âncora de exclusão e contato do DPO', () => {
  const pp = source('../src/pages/legal/PrivacyPolicyPage.tsx')
  assert.match(pp, /id="exclusao-de-dados"/)
  assert.match(pp, /contato\.raffasp@gmail\.com/)
  assert.match(pp, /Exclusão de dados/)
})

test('HelpPage trocou marca e FAQ de modo de teste do Meta', () => {
  const help = source('../src/pages/HelpPage.tsx')
  assert.match(help, /sobre o Auto Orbital/i)
  assert.match(help, /em modo de desenvolvimento/)
  assert.doesNotMatch(help, /Shopee Auto Vendas/)
})

test('Termos e Política têm comentário de revisão jurídica', () => {
  const terms = source('../src/pages/legal/TermsPage.tsx')
  const pp = source('../src/pages/legal/PrivacyPolicyPage.tsx')
  assert.match(terms, /Revisão jurídica necessária antes de publicação oficial/)
  assert.match(pp, /Revisão jurídica necessária antes de publicação oficial/)
})

test('X aguarda disponibilização em plano pago', () => {
  const limits = source('../src/lib/networkLimits.ts')
  assert.match(limits, /X estará disponível em um plano pago em breve/)
  assert.match(limits, /DISABLED_NETWORKS/)
})
