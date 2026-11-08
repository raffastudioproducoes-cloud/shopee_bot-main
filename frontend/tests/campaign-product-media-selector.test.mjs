import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (name) => readFileSync(new URL(name, import.meta.url), "utf8")
const selector = read("../src/components/campaigns/CampaignProductMediaSelector.tsx")
const planner = read("../src/components/campaigns/CampaignPlanner.tsx")
const visual = read("../src/components/products/ProductMediaVisual.tsx")
const products = read("../src/api/products.ts")

test("campanha consulta galeria persistente sem criar novo upload", () => {
  assert.match(selector, /queryFn: \(\) => productsApi\.media\(productId\)/)
  assert.match(selector, /Usar imagem original da Shopee/)
  assert.match(selector, /selectedIds\.includes\(item\.id\)/)
  assert.match(selector, /onSelectedChange/)
  assert.match(planner, /<CampaignProductMediaSelector productId=\{id\}/)
  assert.match(planner, /product_media_ids: snapshots\[id\]\.selectedProductMediaIds/)
  assert.match(planner, /selectedProductMediaIds: item\.product_media_ids \?\? \[\]/)
  assert.doesNotMatch(planner, /type="file"/)
  assert.doesNotMatch(planner, /campaignsApi\.uploadMedia/)
})

test("miniaturas privadas de vídeos são reutilizadas na campanha e em Produtos", () => {
  assert.match(products, /thumbnail_url\?: string \| null/)
  assert.match(visual, /item\.media_type === "VIDEO" \? item\.thumbnail_url : item\.preview_url/)
  assert.match(selector, /<ProductMediaVisual item=\{item\}/)
  assert.match(visual, /Vídeo salvo/)
})
