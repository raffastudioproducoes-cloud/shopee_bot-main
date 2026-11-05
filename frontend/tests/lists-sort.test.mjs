import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const sortModule = await (async () => {
  try {
    return await import("../src/lib/listSorting.ts")
  } catch (error) {
    if (error?.code !== "ERR_UNKNOWN_FILE_EXTENSION") throw error
    // A CI usa Node 20 e possui TypeScript no devDependencies.
    const ts = await import("typescript")
    const source = readFileSync(new URL("../src/lib/listSorting.ts", import.meta.url), "utf8")
    const { outputText } = ts.transpileModule(source, {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
    })
    return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
  }
})()

const { LIST_SORT_OPTIONS, sortProductLists, isUsageSort, isListSortMode } = sortModule
const records = [
  { id: 4, name: "Zebra", created_at: "2026-10-28T09:00:00", updated_at: null, product_count: 2 },
  { id: 1, name: "Árvore", created_at: "2026-10-29T09:00:00", updated_at: "2026-11-01T09:00:00", product_count: 5 },
  { id: 3, name: "Casa", created_at: "2026-10-30T09:00:00", updated_at: "2026-11-04T09:00:00", product_count: 1 },
  { id: 2, name: "Banho", created_at: "2026-10-31T09:00:00", updated_at: null, product_count: 3 },
]
const usage = { 1: 3, 2: 0, 3: 7, 4: 1 }
const names = (mode) => sortProductLists(records, mode, usage).map((r) => r.name)

test("ordenador oferece os 10 sentidos dos cinco critérios, sem duplicações", () => {
  assert.equal(LIST_SORT_OPTIONS.length, 10)
  assert.equal(new Set(LIST_SORT_OPTIONS.map((o) => o.value)).size, 10)
  assert.ok(isListSortMode("usage-desc"))
  assert.ok(!isListSortMode("arbitrary"))
  assert.ok(isUsageSort("usage-asc"))
  assert.ok(!isUsageSort("created-asc"))
})

test("alfabética em português A-Z e Z-A", () => {
  assert.deepEqual(names("name-asc"), ["Árvore", "Banho", "Casa", "Zebra"])
  assert.deepEqual(names("name-desc"), ["Zebra", "Casa", "Banho", "Árvore"])
})

test("criação recente ou antiga, independentemente da ordem da API", () => {
  assert.deepEqual(names("created-asc"), ["Zebra", "Árvore", "Casa", "Banho"])
  assert.deepEqual(names("created-desc"), ["Banho", "Casa", "Árvore", "Zebra"])
})

test("mais itens e menos itens", () => {
  assert.deepEqual(names("items-desc"), ["Árvore", "Banho", "Zebra", "Casa"])
  assert.deepEqual(names("items-asc"), ["Casa", "Zebra", "Banho", "Árvore"])
})

test("mais nova significa última edição e usa criação quando nunca foi editada", () => {
  assert.deepEqual(names("updated-desc"), ["Casa", "Árvore", "Banho", "Zebra"])
  assert.deepEqual(names("updated-asc"), ["Zebra", "Banho", "Árvore", "Casa"])
})

test("mais usada e menos usada contam campanhas realmente ativadas", () => {
  assert.deepEqual(names("usage-desc"), ["Casa", "Árvore", "Zebra", "Banho"])
  assert.deepEqual(names("usage-asc"), ["Banho", "Zebra", "Árvore", "Casa"])
})

test("não altera o array original nem vaza estatística entre listas", () => {
  const before = [...records]
  sortProductLists(records, "usage-desc", { 1: 99 })
  assert.deepEqual(records, before)
  assert.deepEqual(names("name-asc"), ["Árvore", "Banho", "Casa", "Zebra"])
})

test("integração: busca é aplicada antes da ordenação, uso somente sob demanda", () => {
  const read = (path) => readFileSync(new URL("../src/" + path, import.meta.url), "utf8")
  const lists = read("pages/ListasPage.tsx")
  const api = read("api/lists.ts")
  assert.match(lists, /const visibleLists = sortProductLists\(filteredLists, sortMode, usageQuery\.data\?\.counts\)/)
  assert.match(lists, /enabled: usageSortSelected && Boolean\(user\?\.id\) && Boolean\(listsData\)/)
  assert.match(lists, /label="ORDENAR LISTAS"/)
  assert.match(lists, /options=\{LIST_SORT_OPTIONS\}/)
  assert.match(lists, /localStorage\.setItem\("lists-sort", next\)/)
  assert.match(api, /api\.get<ListUsageResponse>\('\/lists\/usage'\)/)
})
