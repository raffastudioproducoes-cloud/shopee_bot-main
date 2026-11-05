import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = {
  shell: readFileSync(new URL("../src/pages/PanelPage.tsx", import.meta.url), "utf8"),
  page: readFileSync(new URL("../src/pages/ProductsPage.tsx", import.meta.url), "utf8"),
  store: readFileSync(new URL("../src/stores/productsSearchStore.ts", import.meta.url), "utf8"),
}

test("topbar mostra busca em Meus Produtos e oculta apenas na Pesquisa Avançada", () => {
  assert.match(source.shell, /activeProductsTab = useProductsSearchStore\(\(state\) => state\.activeTab\)/)
  assert.match(source.shell, /showSearch=\{location\.pathname !== '\/app' && \(location\.pathname !== '\/products' \|\| activeProductsTab === 'mine'\)\}/)
  assert.match(source.store, /activeTab: "mine"/)
  assert.match(source.store, /setActiveTab: \(tab: "mine" \| "catalog"\) => void/)
})

test("as abas compartilham estado com o layout sem apagar a busca de Meus Produtos", () => {
  assert.match(source.page, /activeTab = useProductsSearchStore\(\(state\) => state\.activeTab\)/)
  assert.match(source.page, /setActiveTab = useProductsSearchStore\(\(state\) => state\.setActiveTab\)/)
  assert.doesNotMatch(source.page, /useState<ProductsTab>\("mine"\)/)
  assert.match(source.page, /setActiveTab\(saved\?\.activeTab === "catalog" \? "catalog" : "mine"\)/)
  assert.match(source.shell, /location\.pathname === "\/products" \? productsSearch/)
  assert.match(source.store, /setQuery: \(query\) => set\(\{ query \}\)/)
  assert.match(source.page, /<CatalogSearchTab /)
})

test("outras rotas mantêm suas regras atuais de busca", () => {
  assert.match(source.shell, /location\.pathname === "\/posts" \? postsSearch/)
  assert.match(source.shell, /location\.pathname === "\/posts"/)
  assert.match(source.shell, /location\.pathname !== '\/app'/)
})
