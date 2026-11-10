import test from "node:test"
import assert from "node:assert/strict"
import { readdirSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { join, relative } from "node:path"

const root = fileURLToPath(new URL("../src", import.meta.url))

// Única exceção a animate-spin: spinners de ação/estado pontual, identificados por
// arquivo + trecho vizinho. Nenhuma página/arquivo inteiro é isento.
const spinnerAllowlist = {
  "components/ui/Button.tsx": [/className=\{loading \? "animate-spin" : undefined\}/], // botão em loading
  "components/ui/Toaster.tsx": [/t\.kind === "loading" \? "animate-spin"/], // toast de operação em andamento
  "pages/LoginPage.tsx": [/<Icon name="loader-2" size=\{18\} className="animate-spin" \/>/], // botão de submit
  "pages/PostsPage.tsx": [/publishMutation\.isPending && publishMutation\.variables === post\.id \? "animate-spin"/], // botão publicar
  "components/ui/SlideToConfirm.tsx": [/name=\{loading \? "loader-2" : "chevrons-right"\} size=\{20\} className=\{loading \? "animate-spin"/], // alça "Ativando…"
  "pages/CredentialsPage.tsx": [/testing \? \(\s*<Icon name="loader-2"[^>]*className="animate-spin"/], // indicador "testando conexão"
}

function files(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    return entry.isDirectory() ? files(path) : path.endsWith(".tsx") ? [path] : []
  })
}

const sources = files(join(root, "pages")).concat(files(join(root, "components"))).map((file) => ({
  rel: relative(root, file).replaceAll("\\", "/"),
  text: readFileSync(file, "utf8"),
}))

test("nenhuma página ou componente usa o texto Carregando...", () => {
  const violations = sources.filter(({ text }) => /Carregando\.\.\./.test(text)).map(({ rel }) => rel)
  assert.deepEqual(violations, [])
})

test("animate-spin só aparece em trechos permitidos de botão/ação, por arquivo", () => {
  const violations = []
  for (const { rel, text } of sources) {
    const allowed = spinnerAllowlist[rel] ?? []
    const hits = [...text.matchAll(/animate-spin/g)]
    for (const hit of hits) {
      const window = text.slice(Math.max(0, hit.index - 240), hit.index + 80)
      if (!allowed.some((snippet) => snippet.test(window))) violations.push(`${rel}@${hit.index}: animate-spin fora dos trechos permitidos`)
    }
    if (allowed.length > hits.length) violations.push(`${rel}: allowlist obsoleta (trecho sem animate-spin)`)
  }
  assert.deepEqual(violations, [])
})

test("allowlist aponta apenas para arquivos existentes", () => {
  const known = new Set(sources.map(({ rel }) => rel))
  assert.deepEqual(Object.keys(spinnerAllowlist).filter((rel) => !known.has(rel)), [])
})

test("páginas que carregam dados usam skeleton compartilhado, não marcação própria", () => {
  const offenders = sources
    .filter(({ rel }) => rel.startsWith("pages/") && /isLoading/.test(readFileSync(join(root, rel), "utf8")))
    .filter(({ text }) => /<SkeletonRegion/.test(text))
    .map(({ rel }) => rel)
  // Dashboard e Credenciais/Perfis têm layout próprio documentado; nenhuma outra página pode montar região manual.
  assert.deepEqual(offenders.filter((rel) => !/DashboardPage|CredentialsPage|ProfilesPage/.test(rel)), [])
})

test("API padrão de skeleton existe", () => {
  const file = readFileSync(join(root, "components/ui/Skeleton.tsx"), "utf8")
  assert.match(file, /export function PageSkeleton/)
  assert.match(file, /export function PageState/)
  assert.match(file, /export const SKELETON_ROWS/)
})
