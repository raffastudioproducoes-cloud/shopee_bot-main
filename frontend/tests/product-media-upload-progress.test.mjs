import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const editor = read("../src/components/products/ProductMediaManager.tsx")
const styles = read("../src/components/products/productMediaManager.css")
const products = read("../src/api/products.ts")
const transport = read("../src/lib/api.ts")
const errorFormat = read("../src/lib/apiError.ts")

test("progresso é calculado sobre bytes reais de todos os arquivos, sem simular o processamento", () => {
  assert.match(editor, /selected\.reduce\(\(sum, file\) => sum \+ file\.size, 0\)/)
  assert.match(editor, /Math\.round\(100 \* \(sentBytes \+ file\.size \* fraction\) \/ totalBytes\)/)
  assert.match(editor, /setPhase\("processing"\)/)
  assert.match(editor, /Transferido; processando mídia/)
  assert.match(editor, /aria-valuenow=\{uploadProgress\}/)
  assert.match(editor, /role="progressbar"/)
  assert.match(editor, /strokeDashoffset=\{RING_CIRCUMFERENCE \* \(1 - uploadProgress \/ 100\)\}/)
})

test("cronômetro mostra tempo decorrido real com avisos graduais, sem porcentagem simulada", () => {
  assert.match(editor, /setProcessingStartedAt\(Date\.now\(\)\)/)
  assert.match(editor, /Date\.now\(\) - processingStartedAt/)
  assert.match(editor, /window\.setInterval\(updateElapsed, 1000\)/)
  assert.match(editor, /window\.clearInterval\(interval\)/)
  assert.match(editor, /seconds >= 15/)
  assert.match(editor, /seconds >= 30/)
  assert.match(editor, /seconds >= 60/)
  assert.match(editor, /seconds >= 120/)
  assert.match(editor, /Tempo de processamento:/)
  assert.match(editor, /aria-live="off"/)
  assert.match(editor, /phase !== "idle"/)
  assert.match(editor, /phase === "error" && error/)
  assert.match(editor, /setPhase\("success"\)/)
  assert.match(editor, /setPhase\("error"\)/)
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
  assert.match(errorFormat, /typeof obj\.error === "string" && obj\.error/)
})

test("sombra, skeleton e prévias respeitam movimento reduzido e estados de erro", () => {
  assert.match(editor, /<ProductMediaVisual item=\{item\}/)
  assert.match(editor, /product-media-upload-stage__processing-track/)
  assert.match(editor, /window\.setTimeout\(\(\) => setPhase\("idle"\), 2400\)/)
  assert.match(styles, /\.product-media-upload-stage__skeleton/)
  assert.match(styles, /\.product-media-upload-stage__processing-track/)
  assert.match(styles, /box-shadow: var\(--shadow-panel\)/)
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/)
})
