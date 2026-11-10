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
  const css = src('components/ui/motion.css')
  assert.match(motion, /prefers-reduced-motion: reduce/)
  assert.match(motion, /const skip = prefersReducedMotion\(\) \|\| alreadyCounted\(label\)/)
  assert.match(splash, /if \(prefersReducedMotion\(\)\) return false/)
  assert.ok((css.match(/@media \(prefers-reduced-motion: reduce\)/g) ?? []).length >= 4)
})

test('splash pós-login: aparece a cada login e para TODAS as contas (inclusive ADM), não bloqueia cliques e some em até 2,2 s', () => {
  const splash = src('components/ui/PostLoginSplash.tsx')
  const css = src('components/ui/motion.css')
  assert.match(splash, /sessionStorage\.getItem\(SEEN_KEY\) !== '1'/)
  assert.match(splash, /SPLASH_MS = 2200/)
  assert.match(splash, /pointerdown/)
  assert.match(css, /pointer-events: none/)
  assert.match(css, /@property --hole/, 'círculo que se abre revelando o painel')
  assert.match(css, /calc\(var\(--hole\) \+ 16%\)/, 'círculo de borda difusa (sem traço marcado)')
  assert.doesNotMatch(css, /post-login-splash__ring \{[^}]*border:/, 'sem anéis de traço')
  assert.doesNotMatch(src('pages/PanelPage.tsx'), /access !== 'ADMIN' && <PostLoginSplash/, 'ADM também vê a entrada')
  assert.match(src('pages/PanelPage.tsx'), /<PostLoginSplash \/>/)
  // a cada login as flags são zeradas (senão a entrada e as contagens só apareciam na 1ª vez da aba)
  assert.match(src('lib/motion.ts'), /export function resetPostLoginAnimations/)
  assert.match(src('pages/LoginPage.tsx'), /resetPostLoginAnimations\(\)/)
  assert.match(src('router.tsx'), /resetPostLoginAnimations\(\)/)
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
  assert.match(src('components/ui/motion.css'), /\.toast-in \{ animation: none; \}/)
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

test('lote 4: transição de página, pílula do menu, anel de caracteres, brilho do upgrade e foco do login', () => {
  assert.match(src('pages/PanelPage.tsx'), /<div key=\{location\.pathname\} className="page-enter"><Outlet \/><\/div>/)
  const rail = src('components/ui/SideRail.tsx')
  assert.match(rail, /className="app-rail-pill"/)
  assert.match(rail, /li\[data-active="true"\]/)
  assert.match(rail, /aria-hidden="true" className="app-rail-pill"/)
  assert.match(src('components/posts/TextVariantTabs.tsx'), /className=\{`char-ring\$\{bad \? " is-over" : ""\}`\}/)
  const css = src('components/ui/motion.css')
  for (const cls of ['.page-enter', '.app-rail-pill', '.char-ring', '.campaign-remaining']) assert.ok(css.includes(cls), cls)
  assert.match(css, /\.page-enter \{ animation: none; \}/)
  assert.match(css, /\.app-rail-pill \{ transition: none; \}/)
  assert.match(src('components/plans/planSummary.css'), /\.plan-info-button:hover::after/)
  assert.match(src('pages/LoginPage.css'), /\.login-split__form input:focus-visible \{ box-shadow/)
})

test('campanha mostra quantos passos faltam e vira "Tudo pronto" com os 3 passos feitos', () => {
  const planner = src('components/campaigns/CampaignPlanner.tsx')
  assert.match(planner, /escolher a lista e os produtos/)
  assert.match(planner, /definir período e frequência/)
  assert.match(planner, /gerar a prévia do calendário/)
  assert.match(planner, /Tudo pronto para ativar\./)
  assert.match(planner, /i < 3 - pending\.length/)
})

test('animações gerais: cascata em qualquer página, foco dos campos, brilho nos botões, caixas que sobem e avisos ×N', () => {
  const css = src('components/ui/motion.css')
  assert.match(css, /\.page-enter > \* > \* \{ animation: ao-reveal-in/)
  assert.match(css, /\.ao-input:focus \{ box-shadow/)
  assert.match(css, /\.ao-btn--primary:hover::after/)
  assert.match(css, /\.ao-lift:hover \{ transform: translateY\(-3px\)/)
  assert.match(css, /\.toast-count/)
  assert.match(src('components/ui/TextInput.tsx'), /className="ao-input"/)
  assert.match(src('components/ui/Button.tsx'), /ao-btn ao-btn--\$\{variant\}/)
  assert.match(src('components/ui/StatCard.tsx'), /ao-lift/)
  const store = src('stores/toastStore.ts')
  assert.match(store, /count: \(t\.count \?\? 1\) \+ 1/)
  assert.match(src('components/ui/Toaster.tsx'), /toast-count/)
  for (const sel of ['.page-enter > * > *', '.ao-btn::after', '.ao-lift:hover', '.ao-input {']) {
    const at = css.indexOf(sel)
    assert.ok(at >= 0, sel)
  }
  assert.equal((css.match(/prefers-reduced-motion: reduce/g) ?? []).length >= 8, true, 'todo movimento tem caminho de movimento reduzido')
})

test('login: o botão vira "Pronto!" com ✓ antes de abrir o painel (sem movimento reduzido)', () => {
  const login = src('pages/LoginPage.tsx')
  assert.match(login, /setLoginDone\(true\)/)
  assert.match(login, /Pronto!/)
  assert.match(login, /!systemPrefersReducedMotion\(\)/)
  assert.match(src('pages/LoginPage.css'), /login-done-pop/)
})
