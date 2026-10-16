import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const root = new URL("../", import.meta.url)
const text = (file) => readFile(new URL(file, root), "utf8")

test("splash HTML existe antes do bundle, injeta versão e oferece noscript", async () => {
  const html = await text("index.html")
  assert.match(html, /id="site-splash"/)
  assert.match(html, /%APP_VERSION%/)
  assert.match(html, /<noscript>/)
  assert.match(html, /brand\/symbol\.png/)
})

test("OrbitalLoader expõe tamanhos, acessibilidade e movimento reduzido", async () => {
  const component = await text("src/components/ui/OrbitalLoader.tsx")
  const css = await text("src/index.css")
  assert.match(component, /size\?: "sm" \| "md" \| "lg"/)
  assert.match(component, /aria-live="polite"/)
  assert.doesNotMatch(component, /aria-busy/)
  assert.match(css, /prefers-reduced-motion: reduce/) 
})

test("OrbitIcon desconhecido não emite path sem d", async () => {
  const component = await text("src/components/ui/OrbitalLoader.tsx")
  assert.match(component, /if \(!d\) return null/)
})

test("tema não altera --color-primary-light", async () => {
  const css = await text("src/index.css")
  assert.match(css, /--color-primary-light:\s*#EEEAF2/)
})
