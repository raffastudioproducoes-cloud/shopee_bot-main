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
  assert.equal((css.match(/@media \(prefers-reduced-motion: reduce\)/g) ?? []).length, 4)
})

test('splash pós-login: 1 vez por sessão, não bloqueia cliques, some em até 1,2 s e fica fora do admin', () => {
  const splash = src('components/ui/PostLoginSplash.tsx')
  const css = src('components/ui/postLoginSplash.css')
  assert.match(splash, /sessionStorage\.getItem\(SEEN_KEY\) !== '1'/)
  assert.match(splash, /SPLASH_MS = 1200/)
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

test('segurar para confirmar: 700 ms para ponteiro, teclado e leitor de tela confirmam direto', () => {
  const btn = src('components/ui/HoldToConfirmButton.tsx')
  assert.match(btn, /HOLD_MS = 700/)
  assert.match(btn, /event\.key !== "Enter" && event\.key !== " "/)
  assert.match(btn, /event\.detail === 0/)
  assert.match(btn, /onPointerLeave=\{cancel\}/)
  assert.match(src('components/profiles/ConfirmModal.tsx'), /<HoldToConfirmButton/)
  assert.match(src('components/ui/holdToConfirm.css'), /is-static/)
})

test('avisos e erro de login animam entrada/balanço com movimento reduzido desligado', () => {
  assert.match(src('components/ui/Toaster.tsx'), /className="toast-in"/)
  assert.match(src('components/ui/postLoginSplash.css'), /\.toast-in \{ animation: none; \}/)
  const login = src('pages/LoginPage.css')
  assert.match(login, /login-shake/)
  assert.match(login, /prefers-reduced-motion: reduce\) \{ \.csp-login-banner-error \{ animation: none/)
})

test('Planos: só um plano recomendado, com um único selo, e o plano atual marcado', () => {
  const plans = src('components/plans/PlanComparison.tsx')
  assert.equal((plans.match(/Recomendado/g) ?? []).length, 1)
  assert.match(plans, /plan\.key === currentPlan/)
})

test('fonte Mona Sans hospedada no próprio site (a CSP bloqueava o CDN) com licença OFL junto', () => {
  const css = src('styles/tokens/fonts.css')
  assert.doesNotMatch(css, /https?:\/\//)
  assert.match(css, /url\("\/fonts\/mona-sans-latin-wght-normal\.woff2"\)/)
  assert.match(css, /url\("\/fonts\/mona-sans-latin-wght-italic\.woff2"\)/)
  const lic = readFileSync(new URL('../public/fonts/OFL-LICENSE.txt', import.meta.url), 'utf8')
  assert.match(lic, /SIL Open Font License/)
})

test('avisos usam ícone da biblioteca e os cards do dashboard levam à lista, com teclado', () => {
  assert.match(src('components/ui/Toaster.tsx'), /<Icon name="x" size=\{16\} \/>/)
  const dash = src('pages/DashboardPage.tsx')
  for (const to of ['/products', '/posts', '/lists', '/automacao-posts']) assert.ok(dash.includes(`navigate({ to: '${to}' })} name=`))
  const card = src('components/ui/StatCard.tsx')
  assert.match(card, /role=\{onClick \? "link" : undefined\}/)
  assert.match(card, /tabIndex=\{onClick \? 0 : undefined\}/)
  assert.match(card, /e\.key === "Enter" \|\| e\.key === " "/)
})
