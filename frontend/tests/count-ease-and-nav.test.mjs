import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(src('lib/countUp.ts'), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } })
const { countUpEase, countUpValue } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('a contagem começa devagar e acelera até o valor final', () => {
  assert.equal(countUpEase(0), 0)
  assert.equal(countUpEase(1), 1)
  assert.ok(countUpEase(0.5) < 0.5, 'na metade do tempo ainda está abaixo da metade do valor')
  const early = countUpEase(0.2) - countUpEase(0.1)
  const late = countUpEase(0.9) - countUpEase(0.8)
  assert.ok(late > early * 5, 'a velocidade no fim é bem maior que no começo')
  let last = -1
  for (let i = 0; i <= 50; i++) { const v = countUpEase(i / 50); assert.ok(v >= last); last = v }
  assert.equal(countUpEase(Number.NaN), 0)
  assert.equal(countUpEase(5), 1)
})

test('o valor mostrado respeita limites: inteiro, entre 0 e o alvo, e chega ao alvo', () => {
  assert.equal(countUpValue(902, 0), 0)
  assert.equal(countUpValue(902, 1), 902)
  assert.ok(countUpValue(902, 0.5) < 902 / 2)
  assert.ok(Number.isInteger(countUpValue(902, 0.77)))
  assert.equal(countUpValue(0, 0.5), 0)
})

test('análise: números, barras, anel e linha do tempo acompanham a mesma fração da contagem', () => {
  const v = src('components/AnalyticsVisuals.tsx')
  assert.match(v, /useCountProgress\('analises'\)/)
  assert.match(v, /\(value \/ maximum\) \* 424 \* f/, 'barras de comparação')
  assert.match(v, /count \/ max \* 142 \* f/, 'barras por dia da semana')
  assert.match(v, /\* 100 \* f/, 'anel de engajamento')
  assert.match(v, /clipPath: `inset\(0 \$\{\(1 - f\) \* 100\}% 0 0\)`/, 'linha do tempo revelada')
  assert.equal((v.match(/counted\(/g) ?? []).length >= 8, true, 'KPIs e rótulos contam')
})

test('dashboard e análise usam a mesma curva; movimento reduzido mostra o valor final na hora', () => {
  const m = src('lib/motion.ts')
  assert.match(m, /export function useCountProgress/)
  assert.match(m, /setFraction\(countUpEase\(progress\)\)/)
  assert.match(m, /useState\(skip \? 1 : 0\)/)
  assert.match(src('components/ui/StatCard.tsx'), /useCountUp\(/)
})

test('menu: "Análises" fica logo abaixo de "Dashboard"; a análise não está dentro do dashboard', () => {
  const panel = src('pages/PanelPage.tsx')
  const items = [...panel.matchAll(/\{ value: '([^']+)', label: '([^']+)'/g)].map((m) => m[1])
  assert.deepEqual(items.slice(0, 3), ['/app', '/analytics', '/products'])
  assert.doesNotMatch(src('pages/DashboardPage.tsx'), /AnalyticsPage|analises/)
  assert.match(src('router.tsx'), /path: "\/analytics",\s*component: lazyRoute\(AnalyticsPage, "table"\)/)
})

test('ADM entra pelo dashboard: sem desvio para /admin/overview no login, na raiz, em /app e nas páginas legais', () => {
  for (const f of ['pages/LoginPage.tsx', 'pages/PanelPage.tsx', 'pages/legal/LegalLayout.tsx']) {
    assert.doesNotMatch(src(f), /navigate\(\{ to: [^)]*admin\/overview/, f)
  }
  const router = src('router.tsx')
  assert.doesNotMatch(router.match(/const landingRoute[\s\S]*?component: PresentationPage/)?.[0] ?? '', /admin\/overview/)
  assert.doesNotMatch(router.match(/const dashboardRoute = createRoute\(\{[\s\S]*?\r?\n}\)/)?.[0] ?? '', /admin\/overview/)
})
