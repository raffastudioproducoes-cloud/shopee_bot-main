import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"

const css = fs.readFileSync(new URL("../src/index.css", import.meta.url), "utf8")
const component = fs.readFileSync(new URL("../src/components/ui/Skeleton.tsx", import.meta.url), "utf8")

test("skeleton usa tokens, reduz movimento e expõe variantes", () => {
  assert.match(css, /\.skeleton\s*\{/)
  assert.match(css, /prefers-reduced-motion:\s*reduce/)
  assert.match(css, /var\(--graphite-700\)/)
  for (const name of ["SkeletonText", "SkeletonCard", "SkeletonTableRow", "SkeletonAvatar"]) assert.match(component, new RegExp(`export function ${name}`))
  assert.match(component, /aria-busy="true"/)
})
