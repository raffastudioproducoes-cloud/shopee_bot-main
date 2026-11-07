import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"
import ts from "typescript"

async function loadSnapshots() {
  const source = await readFile(new URL("../src/lib/campaignSnapshots.ts", import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
}

const products = [
  { id: 11, name: "Bolsa", image: "https://images.test/11.jpg", commission_link: "https://s.test/a" },
  { id: 12, name: "Tênis", image: null, commission_link: null },
]

test("snapshot pertence ao produto e é independente da lista de origem", async () => {
  const { createCampaignSnapshot, patchCampaignSnapshot } = await loadSnapshots()
  const first = createCampaignSnapshot(products[0])
  assert.deepEqual(first, {
    title: "Bolsa", copy: "", affiliateLink: "https://s.test/a", networks: [],
    networkCopies: {}, useShopeeImage: true,
  })
  const saved = { 11: first, 12: createCampaignSnapshot(products[1]) }
  const changed = patchCampaignSnapshot(saved, 11, { title: "Bolsa exclusiva", copy: "Oferta de hoje" })
  assert.equal(changed[11].title, "Bolsa exclusiva")
  assert.equal(changed[11].copy, "Oferta de hoje")
  assert.equal(changed[12].title, "Tênis")
  assert.equal(saved[11].title, "Bolsa")
  assert.equal(products[0].name, "Bolsa")
  assert.equal(changed[12].useShopeeImage, false)
})

test("restauração preserva campo apagado e isola IDs da lista atual", async () => {
  const { reconcileCampaignSnapshots } = await loadSnapshots()
  const saved = {
    11: { title: "", copy: "", affiliateLink: "", networks: ["threads", "fake"],
      networkCopies: { threads: "", fake: "indevido" }, useShopeeImage: false },
    99: { title: "de outra lista", copy: "fora", networks: ["x"] },
  }
  const restored = reconcileCampaignSnapshots(products, saved)
  assert.deepEqual(Object.keys(restored), ["11", "12"])
  assert.equal(restored[11].title, "")
  assert.equal(restored[11].affiliateLink, "")
  assert.equal(restored[11].useShopeeImage, false)
  assert.deepEqual(restored[11].networks, ["threads"])
  assert.deepEqual(restored[11].networkCopies, { threads: "" })
  assert.equal(restored[12].title, "Tênis")
})

test("snapshot inválido não mantém foto inexistente nem rede proibida", async () => {
  const { reconcileCampaignSnapshots } = await loadSnapshots()
  const restored = reconcileCampaignSnapshots(products, {
    12: { title: "Tênis", copy: "Confira", affiliateLink: "", networks: ["tiktok", "instagram", "kwai"],
      networkCopies: { tiktok: "A", instagram: "B", kwai: "C" }, useShopeeImage: true },
  })
  assert.equal(restored[12].useShopeeImage, false)
  assert.deepEqual(restored[12].networks, ["tiktok", "instagram"])
  assert.deepEqual(restored[12].networkCopies, { tiktok: "A", instagram: "B" })
})

test("seleção global de redes altera todos os itens sem apagar as copies individuais", async () => {
  const { createCampaignSnapshot, setCampaignNetworkForAll } = await loadSnapshots()
  const base = {
    11: { ...createCampaignSnapshot(products[0]), networkCopies: { threads: "Texto A" } },
    12: { ...createCampaignSnapshot(products[1]), networkCopies: { threads: "Texto B" } },
  }
  const checked = setCampaignNetworkForAll(base, [11, 12], "threads", true)
  assert.deepEqual(checked[11].networks, ["threads"])
  assert.deepEqual(checked[12].networks, ["threads"])
  assert.deepEqual(setCampaignNetworkForAll(checked, [11, 12], "threads", true)[11].networks, ["threads"])
  assert.deepEqual(setCampaignNetworkForAll(checked, [11, 12], "threads", false)[12].networks, [])
  assert.equal(checked[11].networkCopies.threads, "Texto A")
  assert.equal(checked[12].networkCopies.threads, "Texto B")
  assert.deepEqual(base[11].networks, [], "não altera o rascunho original por referência")
  assert.equal(setCampaignNetworkForAll(checked, [999], "facebook", true)[999], undefined)
})
