import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(src('lib/countUp.ts'), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } })
const { countUpValue } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('contagem vai de 0 ao valor real, sem ultrapassar e sem decrescer', () => {
  assert.equal(countUpValue(120, 0), 0)
  assert.equal(countUpValue(120, 1), 120)
  assert.equal(countUpValue(120, 5), 120)
  let last = -1
  for (let i = 0; i <= 20; i++) {
    const v = countUpValue(120, i / 20)
    assert.ok(v >= last && v <= 120)
    last = v
  }
})

test('contagem trata alvo inválido, zero e progresso fora da faixa', () => {
  assert.equal(countUpValue(0, 0.5), 0)
  assert.equal(countUpValue(Number.NaN, 0.5), 0)
  assert.equal(countUpValue(-3, 0.5), 0)
  assert.equal(countUpValue(10, -1), 0)
})

test('movimento reduzido desliga contagem, splash e cascata', () => {
  const motion = src('lib/motion.ts')
  const splash = src('components/ui/PostLoginSplash.tsx')
  const css = src('components/ui/postLoginSplash.css')
  assert.match(motion, /prefers-reduced-motion: reduce/)
  assert.match(motion, /prefersReducedMotion\(\) \|\| !Number\.isFinite\(target\)/)
  assert.match(splash, /if \(prefersReducedMotion\(\)\) return false/)
  assert.equal((css.match(/@media \(prefers-reduced-motion: reduce\)/g) ?? []).length, 3)
})

test('splash pós-login: 1 vez por sessão, não bloqueia cliques, some em até 2,5 s e fica fora do admin', () => {
  const splash = src('components/ui/PostLoginSplash.tsx')
  const css = src('components/ui/postLoginSplash.css')
  assert.match(splash, /sessionStorage\.getItem\(SEEN_KEY\) !== '1'/)
  assert.match(splash, /SPLASH_MS = 1600/)
  assert.match(splash, /pointerdown/)
  assert.match(css, /pointer-events: none/)
  assert.match(src('pages/PanelPage.tsx'), /user\?\.access !== 'ADMIN' && <PostLoginSplash \/>/)
})

test('dashboard: cards com cascata e contagem só para inteiros', () => {
  const dash = src('pages/DashboardPage.tsx')
  assert.equal((dash.match(/className="ao-reveal"/g) ?? []).length, 4)
  const card = src('components/ui/StatCard.tsx')
  assert.match(card, /\/\^\\d\+\$\/\.test\(price\)/)
})

test('copiar e-mail confirma com "Copiado!"', () => {
  const help = src('pages/HelpPage.tsx')
  assert.match(help, /"Copiado!"/)
  assert.match(help, /\.catch\(\(\) => undefined\)/)
})
