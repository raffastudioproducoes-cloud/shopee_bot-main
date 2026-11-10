import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')

test('login usa a animação three.js sob demanda, com quadro parado para movimento reduzido e sem WebGL', () => {
  const page = src('pages/LoginPage.tsx')
  assert.match(page, /lazy\(\(\) => import\('\.\.\/components\/login\/LoginOrbitScene'\)\)/)
  assert.match(page, /prefersReducedMotion \? <LoginOrbitStill \/>/)
  assert.match(page, /<Suspense fallback=\{<LoginOrbitStill \/>\}>/)
  assert.doesNotMatch(page, /login-bg\.mp4/)
  const comp = src('components/login/LoginOrbitScene.tsx')
  assert.match(comp, /aria-hidden="true"/)
  assert.match(comp, /setFailed\(true\)/)
})

test('a cena pausa fora da tela/aba, limita a resolução e libera a GPU ao desmontar', () => {
  const scene = src('components/login/orbitScene.ts')
  assert.match(scene, /IntersectionObserver/)
  assert.match(scene, /visibilitychange/)
  assert.match(scene, /Math\.min\(window\.devicePixelRatio \|\| 1, 1\.5\)/)
  assert.match(scene, /renderer\.dispose\(\)/)
  assert.doesNotMatch(scene, /innerHTML|document\.write|eval\(/)
})

test('roteiro: caos, organização e fechamento com a frase', () => {
  const scene = src('components/login/orbitScene.ts')
  for (const w of ['Copia.', 'Cola.', 'Posta.', 'Repete.', 'Chega.']) assert.ok(scene.includes(`'${w}'`), w)
  assert.match(src('components/login/LoginOrbitStill.tsx'), /Do caos à órbita\./)
})
