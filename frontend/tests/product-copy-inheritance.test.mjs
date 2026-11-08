import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import ts from "typescript"

const source = await readFile(new URL("../src/lib/productCopy.ts", import.meta.url), "utf8")
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
})
const { inheritProductCopy } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)

test("publicar agora e recorrência herdam a descrição atual quando ainda não há texto local", () => {
  assert.equal(inheritProductCopy("", null, "  Descrição de Produtos  "), "Descrição de Produtos")
  assert.equal(inheritProductCopy("Descrição antiga", "Descrição antiga", "Descrição nova"), "Descrição nova")
  assert.equal(inheritProductCopy("Descrição antiga", "Descrição antiga", null), "")
})

test("texto manual ou gerado por IA na postagem nunca é sobrescrito pelo catálogo", () => {
  assert.equal(inheritProductCopy("Texto escrito aqui", null, "Base do produto"), "Texto escrito aqui")
  assert.equal(inheritProductCopy("Nova copy por IA", "Base anterior", "Base atualizada"), "Nova copy por IA")
  assert.equal(inheritProductCopy("", null, null), "")
})
