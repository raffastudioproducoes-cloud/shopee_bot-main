import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

const root = join(process.cwd(), "src")
const allowlist = [
  /Button\.tsx$/, // loading de ação: feedback do clique, não da página
  /LoginPage\.tsx$/, // submit de login/cadastro/troca de senha
  /ListasPage\.tsx$/, /ProductsPage\.tsx$/, /PostsPage\.tsx$/, /CredentialsPage\.tsx$/, /ProfilesPage\.tsx$/,
  /Toaster\.tsx$/, // toast global: spinner pequeno de operação em andamento
]

function files(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    return entry.isDirectory() ? files(path) : path.endsWith(".tsx") ? [path] : []
  })
}

test("guardião de skeleton não deixa loading textual ou spinner de página", () => {
  const candidates = files(join(root, "pages")).concat(files(join(root, "components")))
  const violations = []
  for (const file of candidates) {
    const source = readFileSync(file, "utf8")
    if (allowlist.some((pattern) => pattern.test(file))) continue
    if (/Carregando\.\.\./.test(source)) violations.push(`${file}: texto Carregando...`)
    if (/animate-spin/.test(source) && !/Button\.tsx$/.test(file)) violations.push(`${file}: animate-spin fora de botão`)
  }
  assert.deepEqual(violations, [], violations.join("\n"))
})

test("API padrão de skeleton existe", () => {
  const file = readFileSync(join(root, "components/ui/Skeleton.tsx"), "utf8")
  assert.match(file, /export function PageSkeleton/)
  assert.match(file, /export function PageState/)
})
