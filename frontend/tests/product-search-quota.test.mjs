import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { createRequire } from "node:module"
import vm from "node:vm"
import ts from "typescript"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"

const require = createRequire(import.meta.url)
async function moduleAt(path, mocks = {}) {
  const source = await readFile(new URL("../src/" + path, import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } })
  const module = { exports: {} }
  vm.runInNewContext(outputText, { module, exports: module.exports,
    require: (name) => name in mocks ? mocks[name] : name.endsWith(".css") ? {} : require(name),
  })
  return module.exports
}

const plan = (tier = "free", admin = false) => ({
  plan_tier: tier, is_admin: admin,
  resources: { products: { used: 6, limit: admin ? null : tier === "premium" ? 2000 : tier === "pro" ? 500 : 100,
    unlimited: admin, usage_status: "available" } },
})

test("cota compacta não repete a tag de plano e mostra upgrade só Free/Pro", async () => {
  const { ProductQuotaBar } = await moduleAt("components/plans/ProductQuotaBar.tsx")
  const htmlFree = renderToStaticMarkup(React.createElement(ProductQuotaBar, {
    plan: plan("free"), loading: false, error: false, onUpgrade() {},
  }))
  assert.match(htmlFree, /6 de 100 utilizados/)
  assert.match(htmlFree, /Melhorar plano/)
  assert.doesNotMatch(htmlFree, /Administrador|Plano da conta|Conhecer planos/)

  const htmlPremium = renderToStaticMarkup(React.createElement(ProductQuotaBar, {
    plan: plan("premium"), loading: false, error: false, onUpgrade() {},
  }))
  assert.match(htmlPremium, /6 de 2\.000 utilizados/)
  assert.doesNotMatch(htmlPremium, /Melhorar plano/)

  const htmlAdmin = renderToStaticMarkup(React.createElement(ProductQuotaBar, {
    plan: plan("free", true), loading: false, error: false, onUpgrade() {},
  }))
  assert.match(htmlAdmin, /sem cota comercial/)
  assert.doesNotMatch(htmlAdmin, /Melhorar plano/)
})

test("a página de produtos mantém busca e direciona upgrade a planos", async () => {
  const source = await readFile(new URL("../src/pages/ProductsPage.tsx", import.meta.url), "utf8")
  assert.match(source, /debouncedSearch/)
  assert.match(source, /ProductQuotaBar/)
  assert.match(source, /to: "\/settings", hash: "planos"/)
  assert.doesNotMatch(source, /<PlanSummary/)
})

test("as cotas e avisos ficam na seção de planos de Configurações", async () => {
  const source = await readFile(new URL("../src/components/plans/PlanComparison.tsx", import.meta.url), "utf8")
  assert.match(source, /id="planos"/)
  for (const term of ["2.000", "500", "100", "Campanhas", "contratação", "Premium"]) {
    assert.ok(source.toLocaleLowerCase("pt-BR").includes(term.toLocaleLowerCase("pt-BR")))
  }
})
