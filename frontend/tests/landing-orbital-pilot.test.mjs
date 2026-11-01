import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const read = (path) => readFile(new URL('../' + path, import.meta.url), 'utf8')

test('piloto cinematografico permanece em rota publica isolada, sem alterar a landing', async () => {
  const router = await read('src/router.tsx')
  const landing = await read('src/pages/PresentationPage.tsx')
  assert.match(router, /path:\s*["']\/presentation\/pilot["']/)
  assert.match(router, /component:\s*lazyRoute\(OrbitalPilotPage/)
  assert.match(router, /path:\s*["']\/presentation["']/)
  assert.match(router, /component:\s*PresentationPage/)
  assert.match(landing, /id="virada"/)
  assert.match(landing, /Movimento cinematográfico futuro/)
})

test('piloto usa marca original e apresenta a narrativa sem audio ou terceiros', async () => {
  const pilot = await read('src/pages/OrbitalPilotPage.tsx')
  assert.match(pilot, /src="\/brand\/wordmark\.png"/)
  assert.match(pilot, /src="\/brand\/symbol\.png"/)
  assert.match(pilot, /Do caos/)
  assert.match(pilot, /sem áudio/)
  assert.doesNotMatch(pilot, /<audio\b|new Audio\(|<video\b/)
  assert.doesNotMatch(pilot, /https?:\/\/[^\s"']+/)
  const brand = await read('public/brand/README.md')
  assert.match(brand, /logo-full\.png/)
})

test('piloto suporta timeline manual, pausa e reducao de movimento', async () => {
  const pilot = await read('src/pages/OrbitalPilotPage.tsx')
  const css = await read('src/pages/OrbitalPilotPage.css')
  assert.match(pilot, /requestAnimationFrame\(animate\)/)
  assert.match(pilot, /cancelAnimationFrame\(frame\)/)
  assert.match(pilot, /type="range"/)
  assert.match(pilot, /prefers-reduced-motion: reduce/)
  assert.match(pilot, /reducedMotion \? 1 : time \/ DURATION_MS/)
  assert.match(css, /@media \(max-width: 760px\)/)
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/)
})
