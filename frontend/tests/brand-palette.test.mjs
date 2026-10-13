import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const css = readFileSync(new URL("../src/styles/tokens/colors.css", import.meta.url), "utf8")
const EXPECTED = {
  "brand-event-horizon": "#010719", "brand-deep-orbit-navy": "#091959", "brand-deep-blue": "#102B9B",
  "brand-electric-blue": "#1A5BE1", "brand-orbit-blue": "#279CF5", "brand-electric-cyan": "#1FD3FD",
  "brand-ice-blue": "#5D99F8", "brand-indigo": "#6160E8", "brand-orbital-violet": "#936CF2",
  "brand-soft-lilac": "#D4ABE9", "brand-horizon-warm-light": "#FAD2AD", "brand-text": "#EEEAF2",
  "graphite-950": "#080C16", "graphite-900": "#0D1320", "graphite-850": "#121927",
  "graphite-800": "#192130", "graphite-700": "#222B3A",
}

test("tokens da paleta Auto Orbital com hex exatos", () => {
  for (const [name, hex] of Object.entries(EXPECTED)) {
    assert.match(css, new RegExp(`--${name}:${hex};`, "i"), `--${name} deve ser ${hex}`)
  }
})

test("gradiente orbital exato", () => {
  assert.ok(css.includes("--gradient-orbital:linear-gradient(90deg,#1FD3FD 0%,#279CF5 30%,#6160E8 65%,#936CF2 100%)"))
})
