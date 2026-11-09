import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"
import ts from "typescript"

async function loadSchedule() {
  const source = await readFile(new URL("../src/lib/campaignSchedule.ts", import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
}

test("conta somente weekdays selecionados e calcula saldo real do plano", async () => {
  const { countSelectedWeekdays, calculateCampaignScheduleUsage } = await loadSchedule()
  const weekdays = [0, 2, 4, 6] // segunda, quarta, sexta e domingo
  assert.equal(countSelectedWeekdays("2026-11-01", "2026-11-30", weekdays), 18)

  const usage = calculateCampaignScheduleUsage({
    startDate: "2026-11-01",
    endDate: "2026-11-30",
    weekdays,
    activeDayLimit: 30,
    startTime: "09:00",
    endTime: "18:00",
    postsPerDay: 2,
  })
  assert.equal(usage.activeDaysUsed, 18)
  assert.equal(usage.activeDaysRemaining, 12)
  assert.equal(usage.lastPostingTime, "18:00")
  assert.equal(usage.maxEndDate, "2026-12-21")
})

test("limite final é a 30ª ocorrência semanal, não o 30º dia corrido", async () => {
  const { maxEndDateForSelectedWeekdays } = await loadSchedule()
  assert.equal(
    maxEndDateForSelectedWeekdays("2026-11-01", [0, 2, 4, 6], 30),
    "2026-12-21",
  )
  assert.equal(
    maxEndDateForSelectedWeekdays("2026-11-01", [0], 30),
    "2027-05-24",
  )
})

test("ativação pode preparar snapshot automaticamente e salvar rascunho segue opcional", async () => {
  const planner = await readFile(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  const css = await readFile(new URL("../src/components/campaigns/campaignPlanner.css", import.meta.url), "utf8")
  assert.match(planner, /activateAfterSave: true/)
  assert.match(planner, /Salvar rascunho manualmente é opcional/)
  assert.match(planner, /activationBlockReason/)
  assert.match(css, /background:var\(--mint-400\)/)
  assert.match(css, /color:var\(--text-on-mint\)/)
})
