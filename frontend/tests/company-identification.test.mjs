import assert from "node:assert/strict"
import test from "node:test"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

const root = new URL("../", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")
const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8")

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })
}

test("dados da empresa ficam em src/lib/company.ts com CNPJ e sem CPF", () => {
  const company = read("src/lib/company.ts")
  assert.ok(company.includes("63.621.332/0001-03"))
  assert.ok(company.includes("63.621.332 RAFAEL MACHADO GALVAO"))
  assert.ok(company.includes("Rua Luiz Montezuma, 59"))
  assert.ok(company.includes("23.088-380"))
  assert.match(company, /contato\.raffasp@gmail\.com/)
})

test("Termos e Privacidade, em PT e EN, trazem a identificação do controlador", () => {
  for (const file of ["TermsPage", "TermsEn", "PrivacyPolicyPage", "PrivacyPolicyEn"]) {
    assert.match(read(`src/pages/legal/${file}.tsx`), /<CompanyIdentification lang="(pt|en)"/, file)
  }
  const block = read("src/pages/legal/CompanyIdentification.tsx")
  assert.match(block, /Identificação do controlador/)
  assert.match(block, /Controller identification/)
  assert.match(block, /art\. 5º, VI/)
  assert.match(block, /art\. 5, VI/)
  assert.match(block, /COMPANY\.cnpj/)
  assert.doesNotMatch(block, /encarregado|DPO/i)
})

test("rodapé da landing mostra a linha curta da empresa", () => {
  const body = read("src/pages/presentation/PresentationBody.tsx")
  const footer = body.slice(body.indexOf("<footer"), body.indexOf("</footer>"))
  assert.match(footer, /COMPANY\.footerLine/)
  assert.ok(read("src/lib/company.ts").includes("Raffa Studio Produções · CNPJ 63.621.332/0001-03 · Rio de Janeiro/RJ"))
})

test("o CPF do titular não aparece em nenhum arquivo de src nem de public", () => {
  const files = [...walk(join(root, "src")), ...walk(join(root, "public"))]
  for (const file of files) {
    if (!/\.(tsx?|css|html|json|svg|txt|xml|md|mjs|js)$/.test(file)) continue
    const text = readFileSync(file, "utf8")
    assert.ok(!text.includes("374.868.338-32") && !text.includes("37486833832"), file)
  }
})
