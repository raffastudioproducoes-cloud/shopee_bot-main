import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = {
  shell: readFileSync(new URL("../src/pages/PanelPage.tsx", import.meta.url), "utf8"),
  page: readFileSync(new URL("../src/pages/ProductsPage.tsx", import.meta.url), "utf8"),
  store: readFileSync(new URL("../src/stores/productsSearchStore.ts", import.meta.url), "utf8"),
  search: readFileSync(new URL("../src/lib/pageSearch.ts", import.meta.url), "utf8"),
}

test("TopBar usa o contexto da rota e continua oculto na Pesquisa Avançada", () => {
  assert.match(source.shell, /activeProductsTab = useProductsSearchStore/)
  assert.match(source.shell, /searchPageForRoute\(location\.pathname, activeProductsTab\)/)
  assert.match(source.shell, /showSearch=\{searchPage !== null\}/)
  assert.match(source.search, /pathname === "\/products"/)
  assert.match(source.search, /productsTab === "mine" \? "products" : null/)
  assert.match(source.store, /activeTab: "mine"/)
})

test("as abas compartilham estado sem perder busca anterior de Produtos", () => {
  assert.match(source.page, /activeTab = useProductsSearchStore\(\(state\) => state\.activeTab\)/)
  assert.match(source.page, /setActiveTab = useProductsSearchStore\(\(state\) => state\.setActiveTab\)/)
  assert.doesNotMatch(source.page, /useState<ProductsTab>\("mine"\)/)
  assert.match(source.page, /setActiveTab\(saved\?\.activeTab === "catalog" \? "catalog" : "mine"\)/)
  assert.match(source.shell, /searchPage === 'products' \? productsSearch/)
  assert.match(source.store, /setQuery: \(query\) => set\(\{ query \}\)/)
  assert.match(source.page, /<CatalogSearchTab /)
})

test("Posts e Listas possuem busca separada, Dashboard não possui", () => {
  assert.match(source.search, /pathname === "\/posts"/)
  assert.match(source.search, /pathname === "\/lists"/)
  assert.match(source.shell, /searchPage === 'posts' \? postsSearch/)
  assert.match(source.shell, /searchPage === 'lists' \? listsSearch/)
  assert.match(source.shell, /setListsSearch\(query\)/)
})
