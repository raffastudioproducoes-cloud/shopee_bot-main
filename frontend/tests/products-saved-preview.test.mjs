import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const files = {
  page: new URL("../src/pages/ProductsPage.tsx", import.meta.url),
  card: new URL("../src/components/ui/TimelineListCard.tsx", import.meta.url),
  preview: new URL("../src/components/products/ProductSavedPersonalization.tsx", import.meta.url),
  editor: new URL("../src/components/products/ProductMediaManager.tsx", import.meta.url),
}
const source = Object.fromEntries(Object.entries(files).map(([key, url]) => [key, readFileSync(url, "utf8")]))

test("a prévia usa a descrição persistida e mídia autenticada do produto", () => {
  assert.match(source.page, /description=\{product\.description\}/)
  assert.match(source.page, /productId=\{product\.id\}/)
  assert.match(source.preview, /const savedCopy = description\?\.trim\(\)/)
  assert.match(source.preview, /productsApi\.media\(productId\)/)
  assert.match(source.preview, /queryKey:\s*\["product-media", productId\]/)
  assert.match(source.editor, /const queryKey = \["product-media", productId\] as const/)
  assert.doesNotMatch(source.preview, /uploadMedia|deleteMedia|productsApi\.update/)
})

test("mídia só é buscada quando o card é expandido e existe estado de erro/vazio", () => {
  assert.match(source.card, /expandedFooter\?: ReactNode/)
  assert.match(source.card, /\{open \? \([\s\S]*\{expandedFooter \? \(/)
  assert.match(source.page, /expandedFooter=\{<ProductSavedPersonalization/)
  assert.match(source.preview, /mediaQuery\.isPending/)
  assert.match(source.preview, /mediaQuery\.isError/)
  assert.match(source.preview, /mediaQuery\.isSuccess && items\.length === 0/)
  assert.match(source.preview, /mediaQuery\.refetch\(\)/)
})

test("imagens e vídeos permitem visualização ampliada sem edição", () => {
  assert.match(source.preview, /item\.media_type === "VIDEO"/)
  assert.match(source.preview, /setSelected\(item\)/)
  assert.match(source.preview, /aria-label=\{`\$\{item\.media_type/)
  assert.match(source.preview, /<Modal open=\{selected !== null\}/)
  assert.match(source.preview, /selected\?\.media_type === "VIDEO"/)
  assert.match(source.preview, /<video key=\{selected\.id\}[^>]+controls/)
  assert.match(source.preview, /<img src=\{selected\.preview_url\}/)
  assert.match(source.preview, /whiteSpace: "pre-wrap"/)
})
