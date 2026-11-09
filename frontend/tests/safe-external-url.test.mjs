import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"
import ts from "typescript"

async function load() {
  const source = await readFile(new URL("../src/lib/safeExternalUrl.ts", import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
}

test("safeExternalUrl aceita só HTTPS em hosts Shopee e recusa o resto (S-02)", async () => {
  const { safeExternalUrl } = await load()
  for (const ok of ["https://shopee.com.br/p-i.1.2", "https://www.shopee.com.br/p-i.1.2", "https://s.shopee.com.br/AbC"]) {
    assert.ok(safeExternalUrl(ok), ok)
  }
  for (const bad of [null, undefined, "", "javascript:alert(1)", "data:text/html,x", "http://shopee.com.br/p",
    "https://evil.example/p", "https://shopee.com.br.evil.example/p", "https://u:p@shopee.com.br/p",
    "https://shopee.com.br:8443/p", "https://s.shopee.com.br",
    "https://shope.ee/AbC", "https://shp.ee/AbC", " https://shopee.com.br/p", "//shopee.com.br/p"]) {
    assert.equal(safeExternalUrl(bad), undefined, String(bad))
  }
})

test("safeImageUrl aceita só domínios de imagem da Shopee", async () => {
  const { safeImageUrl } = await load()
  assert.ok(safeImageUrl("https://down-br.img.susercontent.com/file/x"))
  assert.ok(safeImageUrl("https://cf.shopee.com.br/file/x"))
  for (const bad of ["https://evil.example/x.jpg", "http://cf.shopee.com.br/x", "javascript:alert(1)", "", null]) {
    assert.equal(safeImageUrl(bad), undefined, String(bad))
  }
})

test("links de produto clicáveis passam por safeExternalUrl", async () => {
  for (const rel of ["../src/pages/ProductsPage.tsx", "../src/components/products/CatalogSearchTab.tsx"]) {
    const src = await readFile(new URL(rel, import.meta.url), "utf8")
    assert.doesNotMatch(src, /href=\{(?:product|form)\.(?:original_link|commission_link|image)\}/, rel)
    assert.match(src, /safeExternalUrl|safeImageUrl/, rel)
  }
})
