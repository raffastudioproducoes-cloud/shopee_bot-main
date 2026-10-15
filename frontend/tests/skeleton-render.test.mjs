import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { runInNewContext } from "node:vm"
import ts from "typescript"

const require = createRequire(import.meta.url)
const { renderToStaticMarkup } = require("react-dom/server")
const React = require("react")

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const code = ts.transpileModule(read("../src/components/ui/Skeleton.tsx"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText
const mod = {}
runInNewContext(code, { exports: mod, require })
const html = (el) => renderToStaticMarkup(el)
const count = (markup, needle) => markup.split(needle).length - 1

test("PageSkeleton: uma única região de status, aria-busy=\"true\", sem aria-live redundante", () => {
  const markup = html(React.createElement(mod.PageSkeleton, { variant: "table" }))
  assert.equal(count(markup, 'role="status"'), 1)
  assert.equal(count(markup, 'aria-busy="true"'), 1)
  assert.doesNotMatch(markup, /aria-live/)
})

test("PageSkeleton: linhas por variante vêm de SKELETON_ROWS", () => {
  assert.deepEqual({ ...mod.SKELETON_ROWS }, { cards: 4, table: 5, list: 4, form: 4, detail: 2 })
  const table = html(React.createElement(mod.PageSkeleton, { variant: "table" }))
  assert.equal(count(table, "skeleton-table-row"), 5)
  const cards = html(React.createElement(mod.PageSkeleton, { variant: "cards" }))
  assert.equal(count(cards, "skeleton-card"), 4)
  const detail = html(React.createElement(mod.PageSkeleton, { variant: "detail" }))
  assert.equal(count(detail, "skeleton-card"), 2)
})

test("PageSkeleton: ação, barra de filtros e contagem sobrescrevem a geometria padrão", () => {
  const markup = html(React.createElement(mod.PageSkeleton, { variant: "cards", action: true, toolbar: true, count: 3 }))
  assert.equal(count(markup, "skeleton-card"), 3)
  assert.match(markup, /width:112px;height:38px/)
  assert.equal(count(markup, "width:86px;height:34px"), 2)
})

test("PageState: mostra skeleton enquanto carrega e o conteúdo depois", () => {
  const child = React.createElement("p", null, "conteudo")
  const loading = html(React.createElement(mod.PageState, { loading: true, skeleton: React.createElement("i", null, "sk") }, child))
  assert.match(loading, /sk/)
  assert.doesNotMatch(loading, /conteudo/)
  const ready = html(React.createElement(mod.PageState, { loading: false }, child))
  assert.match(ready, /conteudo/)
})

test("Listas/Posts/Produtos/Logs reutilizam PageSkeleton em vez de skeleton inline", () => {
  for (const page of ["ListasPage", "PostsPage", "ProductsPage"]) {
    const src = read(`../src/pages/${page}.tsx`)
    assert.match(src, /<PageSkeleton/, `${page} sem PageSkeleton`)
    assert.doesNotMatch(src, /<SkeletonRegion/, `${page} ainda monta skeleton inline`)
  }
  assert.match(read("../src/pages/LogsPage.tsx"), /<PageState/)
})

test("router: rotas lazy têm fallback por rota", () => {
  const src = read("../src/router.tsx")
  assert.match(src, /lazyRoute(LogsPage, "table")/)
  assert.match(src, /lazyRoute(UsersPage, "list")/)
})
