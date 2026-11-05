import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const page = readFileSync(new URL("../src/pages/ListasPage.tsx", import.meta.url), "utf8")
const card = page.slice(page.indexOf("<TimelineListCard"), page.indexOf("<TimelineListCard") + 4400)
const stats = card.slice(card.indexOf("stats={["), card.indexOf("sections={["))
const sections = card.slice(card.indexOf("sections={["), card.indexOf("]}", card.indexOf("sections={[")) + 2)

test("indicadores superiores continuam exibindo quantidade, datas e valor", () => {
  for (const label of ['label: "Produtos"', 'label: "Criada em"', 'label: "Atualizada"', 'label: "Valor (mín.)"']) {
    assert.ok(stats.includes(label), `indicador ausente: ${label}`)
  }
})

test("detalhes do card de Listas exibem somente produtos cadastrados", () => {
  assert.deepEqual([...sections.matchAll(/label: "([^"]+)"/g)].map((match) => match[1]), ["Produtos"])
  assert.match(sections, /list\.products\.slice\(0, 6\)/)
  assert.match(sections, /\{p\.name\}/)
  assert.match(sections, /formatPriceRange\(p\.price_min, null\)/)
  assert.match(sections, /Nenhum produto nesta lista/)
})

test("o nome permanece no cabeçalho sem uma segunda seção e as datas só nos indicadores", () => {
  assert.match(card, /title=\{list\.name\}/)
  assert.doesNotMatch(sections, /label: "Lista"|label: "Criada em"|label: "Atualizada em"/)
  assert.match(stats, /toLocaleDateString\("pt-BR"\)/)
})
