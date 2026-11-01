import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
const read = (path) => readFile(new URL('../' + path, import.meta.url), 'utf8')

test('piloto V2 continua em rota pública isolada e preserva a landing aceita', async () => {
  const router = await read('src/router.tsx')
  const landing = await read('src/pages/PresentationPage.tsx')
  assert.match(router, /path:\s*["']\/presentation\/pilot["']/)
  assert.match(router, /component:\s*lazyRoute\(OrbitalPilotPage/)
  assert.match(router, /path:\s*["']\/presentation["']/)
  assert.match(router, /component:\s*PresentationPage/)
  assert.match(landing, /id="virada"/)
})

test('buraco negro e horizonte de eventos representam a marca original sem alterar pixels', async () => {
  const component = await read('src/pages/OrbitalPilotPage.tsx')
  const css = await read('src/pages/OrbitalPilotPage.css')
  const brand = await read('public/brand/README.md')
  assert.match(component, /src="\/brand\/symbol\.png"/)
  assert.match(component, /src="\/brand\/wordmark\.png"/)
  assert.match(component, /ao-film-original-mark/)
  assert.match(css, /ao-film-arc--front/)
  assert.match(css, /ao-film-event-light/)
  assert.match(brand, /logo-full\.png/)
  assert.doesNotMatch(component, /<audio\b|new Audio\(|<video\b/)
  assert.doesNotMatch(component, /https?:\/\/[^\s"']+/)
})

test('V2 transforma papéis de produtos em anúncios, com câmera e letras cinéticas', async () => {
  const component = await read('src/pages/OrbitalPilotPage.tsx')
  const css = await read('src/pages/OrbitalPilotPage.css')
  assert.match(component, /ao-film-paper-face--product/)
  assert.match(component, /ao-film-paper-face--ad/)
  assert.match(component, /function KineticText/)
  assert.match(component, /rotateX\(/)
  assert.match(component, /rotateY\(/)
  assert.match(component, /rotateZ\(/)
  assert.match(component, /function shot\(/)
  assert.match(css, /perspective:/)
  assert.match(css, /backface-visibility:hidden/)
})

test('V2 mantém scrub, pausa, acessibilidade e indicador de automação planejada', async () => {
  const component = await read('src/pages/OrbitalPilotPage.tsx')
  const css = await read('src/pages/OrbitalPilotPage.css')
  assert.match(component, /requestAnimationFrame\(tick\)/)
  assert.match(component, /cancelAnimationFrame\(frame\)/)
  assert.match(component, /type="range"/)
  assert.match(component, /prefers-reduced-motion: reduce/)
  assert.match(component, /reducedMotion \? 1 : time \/ DURATION_MS/)
  assert.match(component, /EM DESENVOLVIMENTO/)
  assert.match(css, /@media\(max-width:540px\)/)
  assert.match(css, /@media\(prefers-reduced-motion:reduce\)/)
})
