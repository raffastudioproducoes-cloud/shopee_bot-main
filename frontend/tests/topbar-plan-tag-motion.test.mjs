import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

const css = readFileSync(new URL("../src/components/plans/planSummary.css", import.meta.url), "utf8")

test("a etiqueta nasce atrás do cartão e desce apenas quando o badge monta", () => {
  assert.match(css, /\.plan-topbar-account \.active-profile-chip\s*\{[^}]*z-index:\s*2/s)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag\s*\{[^}]*z-index:\s*1/s)
  assert.match(css, /\.plan-topbar-account \.plan-topbar-tag > span\s*\{[^}]*animation:\s*plan-topbar-tag-reveal/s)
  assert.match(css, /@keyframes plan-topbar-tag-reveal\s*\{\s*from\s*\{\s*transform:\s*translateY\(var\(--plan-tag-entry-offset\)\)/)
  assert.match(css, /to\s*\{\s*transform:\s*translateY\(0\)/)
})

test("o deslocamento inicial fica totalmente atrás do perfil em desktop e mobile", () => {
  const desktopProfileHeight = 70
  const desktopVisibleStrip = 24
  const mobileProfileHeight = 47
  const mobileVisibleStrip = 19
  assert.equal(desktopProfileHeight + desktopVisibleStrip - desktopVisibleStrip, desktopProfileHeight)
  assert.equal(mobileProfileHeight + mobileVisibleStrip - mobileVisibleStrip, mobileProfileHeight)
  assert.match(css, /padding-bottom:\s*24px/)
  assert.match(css, /--plan-tag-entry-offset:\s*-24px/)
  assert.match(css, /@media \(max-width:\s*767px\)[\s\S]*padding-bottom:\s*19px/)
  assert.match(css, /--plan-tag-entry-offset:\s*-19px/)
})

test("respeita preferência por movimento reduzido e não altera o JSX do cabeçalho", () => {
  assert.match(css, /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*animation:\s*none/)
  assert.doesNotMatch(css, /animation-iteration-count:\s*infinite/)
})
