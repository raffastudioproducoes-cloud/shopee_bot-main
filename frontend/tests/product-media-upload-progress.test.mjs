import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const editor = read("../src/components/products/ProductMediaManager.tsx")
const styles = read("../src/components/products/productMediaManager.css")
const products = read("../src/api/products.ts")
const transport = read("../src/lib/api.ts")

test("progresso é calculado sobre bytes reais de todos os arquivos, sem simular o processamento", () => {
  assert.match(editor, /selected\.reduce\(\(sum, file\) => sum \+ file\.size, 0\)/)
  assert.match(editor, /Math\.round\(100 \* \(sentBytes \+ file\.size \* fraction\) \/ totalBytes\)/)
  assert.match(editor, /setProcessing\(true\)/)
  assert.match(editor, /Transferido; processando mídia/)
  assert.match(editor, /aria-valuenow=\{uploadProgress\}/)
  assert.match(editor, /role="progressbar"/)
  assert.match(editor, /strokeDashoffset=\{RING_CIRCUMFERENCE \* \(1 - uploadProgress \/ 100\)\}/)
})

test("upload multipart autenticado preserva erros FastAPI e notifica transferência real", () => {
  assert.match(products, /api\.uploadWithProgress<ProductMedia>/)
  assert.match(transport, /xhr\.withCredentials = true/)
  assert.match(transport, /xhr\.upload\.onprogress = \(event\) =>/)
  assert.match(transport, /event\.lengthComputable && event\.total > 0/)
  assert.match(transport, /xhr\.upload\.onload = \(\) => onTransferred\?\.\(\)/)
  assert.match(transport, /formatApiError\(body, xhr\.status\)/)
  assert.match(transport, /xhr\.send\(formData\)/)
  assert.doesNotMatch(transport, /xhr\.setRequestHeader\('Content-Type'/)
})

test("sombra, skeleton e prévias respeitam movimento reduzido e estados de erro", () => {
  assert.match(editor, /<MediaThumbnail item=\{item\}/)
  assert.match(editor, /onLoadedData=\{\(\) => setReady\(true\)\}/)
  assert.match(editor, /onError=\{\(\) => setFailed\(true\)\}/)
  assert.match(styles, /\.product-media-upload-stage__skeleton/)
  assert.match(styles, /\.product-media-card__skeleton/)
  assert.match(styles, /box-shadow: var\(--shadow-panel\)/)
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/)
})
