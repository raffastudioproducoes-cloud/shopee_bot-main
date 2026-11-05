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

test("TopBar usa escopo único para Produtos, Posts e Listas", async () => {
  const source = await file("pages/PanelPage.tsx")
  const search = await file("lib/pageSearch.ts")
  assert.match(source, /searchPageForRoute\(location\.pathname, activeProductsTab\)/)
  assert.match(source, /searchPage === 'products' \? productsSearch/)
  assert.match(source, /searchPage === 'posts' \? postsSearch/)
  assert.match(source, /searchPage === 'lists' \? listsSearch/)
  assert.match(source, /setProductsSearch\(query\)/)
  assert.match(source, /setPostsSearch\(query\)/)
  assert.match(source, /setListsSearch\(query\)/)
  assert.match(source, /showSearch=\{searchPage !== null\}/)
  assert.match(search, /pathname === "\/products"/)
})

test("Barra superior é única e mantém campo controlado", async () => {
  const source = await file("components/ui/TopBar.tsx")
  assert.match(source, /<SearchField value=\{query\} onChange=\{onQuery\}/)
})

test("Cartão de perfil reserva a geometria no carregamento", async () => {
  const chip = await file("components/profiles/ActiveProfileChip.tsx")
  const css = await file("components/plans/planSummary.css")
  assert.match(chip, /active-profile-chip--loading/)
  assert.match(chip, /if \(!isPending\) return null/)
  assert.match(chip, /style=\{chipStyle\}/)
  assert.match(css, /\.plan-topbar-account \.active-profile-chip--loading \{/)
  assert.match(css, /width: 206px/)
  assert.match(css, /active-profile-loading-avatar[\s\S]*?width: 34px !important/)
})

test("Etiqueta de plano só existe depois do carregamento de perfil e plano válidos", async () => {
  const source = await file("components/plans/PlanSummary.tsx")
  assert.match(source, /if \(!activeProfile \|\| query\.isError \|\| !query\.data\) return null/)
  assert.match(source, /if \(label === "Plano indisponível"\) return null/)
})


test("Produtos não mostra botão fantasma à direita durante o carregamento", async () => {
  const source = await file("pages/ProductsPage.tsx")
  assert.match(source, /<PageSkeleton variant="table"[^>]*toolbar/)
  assert.doesNotMatch(source, /<PageSkeleton[^>]*\baction\b/)
})
