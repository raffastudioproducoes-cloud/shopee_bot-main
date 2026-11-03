import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

const src = (path) => readFile(new URL("../src/" + path, import.meta.url), "utf8")

test("todos os ícones do menu lateral são registrados no design system", async () => {
  const [panel, icon] = await Promise.all([
    src("pages/PanelPage.tsx"),
    src("components/ui/Icon.tsx"),
  ])
  const navIcons = [...panel.matchAll(/icon:\s*'([a-z0-9-]+)'/g)].map((match) => match[1])
  const registered = new Set(
    [...icon.matchAll(/^\s*(?:"([a-z0-9-]+)"|([a-z][a-z0-9-]*)):\s*[A-Z]/gm)]
      .map((match) => match[1] ?? match[2]),
  )
  assert.ok(navIcons.includes("square-pen"), "o item Criar POST precisa ter ícone próprio")
  for (const name of navIcons) {
    assert.ok(registered.has(name), "ícone de navegação sem renderização: " + name)
  }
})

test("ícone da ação Calcular prévia também existe no registro", async () => {
  const [campaign, icon] = await Promise.all([
    src("components/campaigns/CampaignPlanner.tsx"),
    src("components/ui/Icon.tsx"),
  ])
  assert.match(campaign, /icon="calendar-search"/)
  assert.match(icon, /"calendar-search":\s*CalendarSearch/)
  assert.match(icon, /\bCalendarSearch\b/)
})
