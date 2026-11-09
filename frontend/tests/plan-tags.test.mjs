import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(read('components/plans/PlanTag.tsx'), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX } })
const { planTierOf } = await import(`data:text/javascript;base64,${Buffer.from(outputText.replace(/import "\.\/planTag\.css"\n?/, '').replace(/from "react\/jsx-runtime"/, 'from "data:text/javascript,export const jsx=()=>null"')).toString('base64')}`)

test('plano da conta vira o estilo certo: admin, premium, pro (plus conta como pro) e free', () => {
  assert.equal(planTierOf({ is_admin: true, plan_tier: 'free' }), 'admin')
  assert.equal(planTierOf({ plan_tier: 'premium' }), 'premium')
  assert.equal(planTierOf({ plan_tier: 'pro' }), 'pro')
  assert.equal(planTierOf({ plan_tier: 'plus' }), 'pro')
  assert.equal(planTierOf({ plan_tier: 'free' }), 'free')
  assert.equal(planTierOf(undefined), 'free')
})

test('CSS: admin rubi/carmesim com brilho, premium na paleta da marca com brilho, free simples sem brilho', () => {
  const css = readFileSync(new URL('../src/components/plans/planTag.css', import.meta.url), 'utf8')
  assert.match(css, /\.plan-tag--admin\s*\{[^}]*tag-ruby[^}]*tag-crimson/s)
  assert.match(css, /\.plan-tag--premium\s*\{[^}]*brand-ice-blue[^}]*brand-orbital-violet[^}]*brand-soft-lilac/s)
  assert.match(css, /\.plan-tag--admin::before, \.plan-tag--premium::before/)
  assert.doesNotMatch(css, /\.plan-tag--free[^{]*::(before|after)/)
  assert.doesNotMatch(css, /\.plan-tag--(free|pro)\s*\{[^}]*animation/s)
  assert.match(css, /prefers-reduced-motion: reduce\) \{ \.plan-tag--admin::after, \.plan-tag--premium::after \{ animation: none/)
})

test('a etiqueta do cabeçalho, o resumo, a tabela de planos e a apresentação usam o mesmo componente', () => {
  assert.match(read('components/plans/PlanSummary.tsx'), /<PlanTag tier=\{planTierOf\(query\.data\)\}>/)
  assert.match(read('components/plans/PlanComparison.tsx'), /<PlanTag tier=/)
  assert.match(read('pages/presentation/Offer.tsx'), /<PlanTag tier=\{plan\.id\}>/)
  const tokens = readFileSync(new URL('../src/styles/tokens/colors.css', import.meta.url), 'utf8')
  for (const t of ['--plan-ruby-deep', '--plan-ruby-bright', '--plan-crimson']) assert.ok(tokens.includes(t))
})
