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
  assert.match(source.card, /expandedHeader\?: ReactNode/)
  assert.match(source.card, /\{open \? \([\s\S]*\{expandedHeader \? \(/)
  assert.match(source.page, /expandedHeader=\{<ProductSavedPersonalization/)
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

test("carrossel navega mídias com setas e mostra no máximo três itens por vez", () => {
  assert.match(source.preview, /useState\(3\)/)
  assert.match(source.preview, /items\.slice\(safeStart, safeStart \+ visibleCount\)/)
  assert.match(source.preview, /width < 270 \? 1 : width < 410 \? 2 : 3/)
  assert.match(source.preview, /aria-label="Mídia anterior"/)
  assert.match(source.preview, /aria-label="Próxima mídia"/)
  assert.match(source.preview, /disabled=\{safeStart === 0\}/)
  assert.match(source.preview, /disabled=\{safeStart >= lastStart\}/)
  assert.match(source.preview, /setCarouselStart\(Math\.min\(lastStart, safeStart \+ 1\)\)/)
  assert.match(source.preview, /ResizeObserver/)
  const mediaPosition = source.preview.indexOf("Imagens e vídeos adicionais")
  const descriptionPosition = source.preview.indexOf("Descrição para redes sociais")
  assert.ok(mediaPosition >= 0 && mediaPosition < descriptionPosition, "a descrição fica depois do carrossel")
})

test("card mantém os cinco indicadores e exibe somente links na timeline", () => {
  const statsStart = source.page.indexOf('stats={[')
  const sectionsStart = source.page.indexOf('sections={[', statsStart)
  const sectionsEnd = source.page.indexOf('\n              ]}', sectionsStart)
  assert.ok(statsStart >= 0 && sectionsStart > statsStart && sectionsEnd > sectionsStart)

  const stats = source.page.slice(statsStart, sectionsStart)
  const sections = source.page.slice(sectionsStart, sectionsEnd)
  for (const title of ["ID Shopee", "Preço", "Comissão", "Ganho/venda", "Cadastrado"]) {
    assert.ok(stats.includes(`label: "${title}"`), `${title} deve permanecer nos indicadores`)
  }
  assert.deepEqual([...sections.matchAll(/label: "([^"]+)"/g)].map((match) => match[1]), ["Links"])
  assert.match(sections, /product\.original_link/)
  assert.match(sections, /product\.commission_link/)
  assert.match(source.page, /expandedHeader=\{<ProductSavedPersonalization/)
  assert.match(source.page, /statsPlacement="bottom"/)
  const headerAt = source.card.indexOf('{expandedHeader ? (')
  const linksAt = source.card.indexOf('{sections.length > 0 ?')
  const bottomStatsAt = source.card.indexOf('{statsPlacement === "bottom" && statsContent ?')
  assert.ok(headerAt >= 0 && headerAt < linksAt && linksAt < bottomStatsAt, "ordem: mídias/descrição, links, indicadores")
})
