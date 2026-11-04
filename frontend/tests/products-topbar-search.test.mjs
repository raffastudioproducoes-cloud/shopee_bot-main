import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const file = async (path) => readFile(new URL("../src/" + path, import.meta.url), "utf8")

test("Produtos não cria um segundo campo de busca no cabeçalho", async () => {
  const source = await file("pages/ProductsPage.tsx")
  assert.doesNotMatch(source, /<SearchField/)
  assert.doesNotMatch(source, /components\/ui\/SearchField/)
  assert.match(source, /useProductsSearchStore/)
  assert.match(source, /debouncedSearch/)
  assert.match(source, /productsApi\.list\(\{ search: debouncedSearch/)
})

test("TopBar usa o mesmo estado de Produtos e preserva busca em Posts", async () => {
  const source = await file("pages/PanelPage.tsx")
  assert.match(source, /location\.pathname === "\/products" \? productsSearch/)
  assert.match(source, /setProductsSearch\(event\.target\.value\)/)
  assert.match(source, /location\.pathname === "\/posts" \? postsSearch/)
  assert.match(source, /setPostsSearch\(event\.target\.value\)/)
  assert.match(source, /showSearch=\{location\.pathname !== '\/app'\}/)
})

test("Barra superior é única e mantém campo controlado", async () => {
  const source = await file("components/ui/TopBar.tsx")
  assert.match(source, /<SearchField value=\{query\} onChange=\{onQuery\}/)
})
