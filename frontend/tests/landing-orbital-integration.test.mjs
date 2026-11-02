import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const read = (path) => readFile(new URL("../" + path, import.meta.url), "utf8")

test("A cena V3.2 entra apenas na seção de virada da landing, carregada sob demanda", async () => {
  const landing = await read("src/pages/PresentationPage.tsx")
  const css = await read("src/pages/PresentationPage.css")
  assert.match(landing, /lazy\(\(\) => import\('\.\/OrbitalPilotPage'\)/)
  assert.match(landing, /function OrbitalLandingScene\(\)/)
  assert.match(landing, /rootMargin: '420px 0px'/)
  assert.match(landing, /<Suspense fallback=\{placeholder\}>/)
  assert.match(landing, /<OrbitalMotionPlayer embedded \/>/)
  assert.match(landing, /id="virada"[\s\S]*<OrbitalLandingScene \/>[\s\S]*id="como-funciona"/)
  assert.match(landing, /Prévia visual em avaliação/)
  assert.doesNotMatch(landing, /ao-lp-turn-symbol/)
  assert.match(css, /\.ao-lp-turn-motion\s*\{/)
  assert.match(css, /\.ao-lp-turn-loading\s*\{/)
})

test("O piloto mantém rota própria, timeline e 10 segundos, sem alterar a cena original", async () => {
  const pilot = await read("src/pages/OrbitalPilotPage.tsx")
  const css = await read("src/pages/OrbitalPilotPage.css")
  const router = await read("src/router.tsx")
  assert.match(router, /path: "\/presentation\/pilot"/)
  assert.match(pilot, /export function OrbitalMotionPlayer\(\{ embedded = false \}/)
  assert.match(pilot, /export default function OrbitalPilotPage\(\)/)
  assert.match(pilot, /const DURATION_MS = 10_000/)
  assert.match(pilot, /const progress = reduced \? 1 : time \/ DURATION_MS/)
  assert.match(pilot, /requestAnimationFrame\(tick\)/)
  assert.match(pilot, /<section ref=\{frameRef\} className="ao3-frame"/)
  assert.match(pilot, /threshold: 0\.35/)
  assert.match(pilot, /if \(!inViewport\) \{ setPlaying\(false\); return \}/)
  assert.match(pilot, /prefers-reduced-motion: reduce/)
  assert.match(pilot, /Estudo criativo, ainda não aprovado/)
  assert.match(css, /\.ao3-embed \.ao3-stage/)
  assert.doesNotMatch(pilot, /<iframe|<video|<audio/)
})
