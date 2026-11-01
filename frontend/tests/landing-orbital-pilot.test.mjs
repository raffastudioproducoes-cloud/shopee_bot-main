import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"
const read = (path) => readFile(new URL("../" + path, import.meta.url), "utf8")

test("V3 permanece em preview isolado, sem substituir apresentação, login ou rota de cliente", async () => {
  const router = await read("src/router.tsx")
  const landing = await read("src/pages/PresentationPage.tsx")
  assert.match(router, /path:\s*["']\/presentation\/pilot["']/)
  assert.match(router, /component:\s*lazyRoute\(OrbitalPilotPage/)
  assert.match(router, /component:\s*PresentationPage/)
  assert.match(landing, /id="virada"/)
})

test("V3 recria universo e horizonte de eventos por Canvas, sem nenhuma imagem ou mídia colada", async () => {
  const source = await read("src/pages/OrbitalPilotPage.tsx")
  const css = await read("src/pages/OrbitalPilotPage.css")
  assert.match(source, /function drawSpace\(canvas: HTMLCanvasElement, progress: number\)/)
  assert.match(source, /createRadialGradient/)
  assert.match(source, /globalCompositeOperation = "lighter"/)
  assert.match(source, /ctx\.ellipse\(/)
  assert.match(source, /ctx\.arc\(/)
  assert.match(source, /<canvas ref=\{ref\}/)
  assert.doesNotMatch(source, /<img\b|<video\b|<audio\b|drawImage\(/)
  assert.doesNotMatch(source, /src\s*=\s*["']\/brand\//)
  assert.doesNotMatch(css, /url\([^)]*\.(png|jpg|jpeg|webp|mp4)/i)
})

test("A timeline conserva seis atos com pausas e a mudança produto para publicidade", async () => {
  const source = await read("src/pages/OrbitalPilotPage.tsx")
  assert.match(source, /const DURATION_MS = 10_000/)
  for (const beat of [".24", ".37", ".43", ".61", ".76", "1.01"]) {
    assert.ok(source.includes("until: " + beat), "falta beat " + beat)
  }
  assert.match(source, /const capture = ease\(/)
  assert.match(source, /const convert = ease\(/)
  assert.match(source, /DIVULGAÇÃO/)
  assert.match(source, /function DashboardReveal/)
  assert.match(source, /function OrbitalSignature/)
  assert.match(source, /function KineticType/)
  assert.match(source, /rotateX\(/)
  assert.match(source, /rotateY\(/)
})

test("Preview tem controle de reprodução, scrub, acessibilidade e bloqueio de motion reduzido", async () => {
  const source = await read("src/pages/OrbitalPilotPage.tsx")
  const css = await read("src/pages/OrbitalPilotPage.css")
  assert.match(source, /requestAnimationFrame\(tick\)/)
  assert.match(source, /cancelAnimationFrame\(frame\)/)
  assert.match(source, /type="range"/)
  assert.match(source, /prefers-reduced-motion: reduce/)
  assert.match(source, /reduced \? 1 : time \/ DURATION_MS/)
  assert.match(source, /aria-label="Explorar quadros da cena"/)
  assert.match(css, /@media\(max-width:580px\)/)
  assert.match(css, /@media\(prefers-reduced-motion:reduce\)/)
  assert.match(source, /EM DESENVOLVIMENTO/)
  assert.match(source, /Estudo criativo, ainda não aprovado/)
})
