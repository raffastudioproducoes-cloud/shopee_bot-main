import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { contextualSearchTerms, matchesScopedSearch, normalizeSearchText, searchPageForRoute } from "../src/lib/pageSearch.ts"

const read = (path) => readFileSync(new URL("../src/" + path, import.meta.url), "utf8")

test("cada rota usa exclusivamente o campo de busca da própria página", () => {
  assert.equal(searchPageForRoute("/lists", "mine"), "lists")
  assert.equal(searchPageForRoute("/posts", "mine"), "posts")
  assert.equal(searchPageForRoute("/products", "mine"), "products")
  assert.equal(searchPageForRoute("/products", "catalog"), null)
  assert.equal(searchPageForRoute("/app", "mine"), null)
  assert.equal(searchPageForRoute("/settings", "mine"), null)
})

test("normalização ignora maiúsculas, acentos, hífen e pontuação", () => {
  assert.equal(normalizeSearchText("  LÊNÇOL — Casal!  "), "lencol casal")
  assert.ok(matchesScopedSearch(["Máquina de café"], "MAQUINA CAFE"))
  assert.ok(matchesScopedSearch(["Organizador em PVC"], "pvc"))
  assert.ok(!matchesScopedSearch(["Furadeira"], "cama"))
})

test("busca contextual encontra objetos de quarto e cozinha", () => {
  assert.ok(matchesScopedSearch(["Lençol casal de algodão"], "quarto"))
  assert.ok(matchesScopedSearch(["Kit colcha e fronha"], "QUARTOS"))
  assert.ok(matchesScopedSearch(["Air Fryer e fritadeira"], "cozinha"))
  assert.ok(matchesScopedSearch(["Sofá de 3 lugares"], "sala"))
  assert.ok(matchesScopedSearch(["Toalha de banho"], "banheiro"))
  assert.ok(!matchesScopedSearch(["Furadeira sem fio"], "quarto"))
})

test("lavadora de carro encontra lava-jato, WAP e VAP", () => {
  assert.ok(matchesScopedSearch(["Hidrolavadora WAP 1500"], "lavadora de carro"))
  assert.ok(matchesScopedSearch(["Equipamento VAP de alta pressão"], "lava a jato"))
  assert.ok(matchesScopedSearch(["Lava-jato potente"], "lavadora de carro"))
  assert.ok(!matchesScopedSearch(["Colcha de solteiro"], "lavadora de carro"))
  assert.ok(contextualSearchTerms("quarto").length <= 26)
})

test("a busca considera apenas os campos recebidos, não outras páginas", () => {
  const lista = ["Ferramentas Elétricas", "Furadeira", "Politriz"]
  assert.ok(matchesScopedSearch(lista, "politriz"))
  assert.ok(matchesScopedSearch(lista, "ferramentas"))
  assert.ok(!matchesScopedSearch(lista, "lençol"))
  assert.ok(matchesScopedSearch(lista, ""))
})

test("TopBar conecta Produtos, Posts e Listas sem campo duplicado", () => {
  const shell = read("pages/PanelPage.tsx")
  const lists = read("pages/ListasPage.tsx")
  const posts = read("components/posts/postPresentation.ts")
  const products = read("pages/ProductsPage.tsx")
  assert.match(shell, /searchPageForRoute\(location\.pathname, activeProductsTab\)/)
  assert.match(shell, /showSearch=\{searchPage !== null\}/)
  assert.match(shell, /query=\{searchValue\}/)
  assert.match(shell, /onQuery=\{searchPage \? \(event\) => setPageSearch\(event\.target\.value\) : undefined\}/)
  assert.match(shell, /useListsSearchStore/)
  assert.match(lists, /matchesScopedSearch\(\[/)
  assert.match(lists, /visibleLists\.map\(\(list\) =>/)
  assert.match(lists, /list\.products \?\? \[\]/)
  assert.match(lists, /listsApi\.list\(\{ limit: 100 \}\)/)
  assert.match(posts, /matchesScopedSearch\(\[postSearchText\(post\)\], query\)/)
  assert.match(products, /productsApi\.list\(\{ search: debouncedSearch/)
  assert.doesNotMatch(products, /<SearchField/)
})
