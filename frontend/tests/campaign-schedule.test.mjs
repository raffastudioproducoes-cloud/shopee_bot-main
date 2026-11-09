import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"
import ts from "typescript"

async function loadPagination() {
  const source = await readFile(new URL("../src/lib/campaignPagination.ts", import.meta.url), "utf8")
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`)
}

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
  assert.match(css, /campaign-weekdays label\.is-on \{[^}]*background:var\(--gradient-cta\)/)
  assert.doesNotMatch(css, /campaign-weekdays label\.is-on \{[^}]*mint/)
})

test("ativação mostra progresso real com cronômetro e confetti respeitando o design system", async () => {
  const planner = await readFile(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  const progress = await readFile(new URL("../src/components/campaigns/ActivationProgress.tsx", import.meta.url), "utf8")
  const confetti = await readFile(new URL("../src/components/ui/ConfettiBurst.tsx", import.meta.url), "utf8")
  const confettiCss = await readFile(new URL("../src/components/ui/confettiBurst.css", import.meta.url), "utf8")
  assert.match(planner, /<ActivationProgress phase=\{activationPhase\}/)
  assert.match(planner, /<ConfettiBurst burstKey=\{confettiKey\}/)
  assert.match(progress, /role="progressbar"/)
  assert.match(progress, /formatElapsed/)
  assert.doesNotMatch(progress, /aria-valuenow=\{\d/)
  assert.match(confetti, /prefers-reduced-motion/)
  assert.doesNotMatch(confetti, /#[0-9a-fA-F]{3,6}/)
  assert.match(confettiCss, /prefers-reduced-motion:reduce/)
})

test("prévia e histórico paginam de 10 em 10 e a seção 06 mostra só contadores relevantes", async () => {
  const lib = await loadPagination()
  const planner = await readFile(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  const api = await readFile(new URL("../src/api/campaigns.ts", import.meta.url), "utf8")
  assert.match(planner, /<CampaignPagination label="Páginas do histórico"/)
  assert.match(planner, /<CampaignPagination label="Páginas da prévia"/)
  assert.match(planner, /relevantProgressCounts\(record\.progress\)/)
  assert.doesNotMatch(planner, /Anteriores|Próximas|offset\+100/)
  assert.match(api, /offset=\$\{offset\}&limit=\$\{limit\}/)
  {
    assert.equal(lib.CAMPAIGN_PAGE_SIZE, 10)
    assert.equal(lib.campaignPageCount(450), 45)
    assert.equal(lib.campaignPageCount(0), 1)
    assert.deepEqual(lib.campaignPageWindow(1, 45), [1, 2, "…", 45])
    assert.deepEqual(lib.campaignPageWindow(20, 45), [1, "…", 19, 20, 21, "…", 45])
    assert.deepEqual(lib.campaignPageWindow(3, 4), [1, 2, 3, 4])
    const counts = lib.relevantProgressCounts({ total: 450, planned: 450, running: 0, succeeded: 0, failed: 0, unknown: 0, cancelled: 0 })
    assert.deepEqual(counts.map((c) => c.key), ["planned"])
  }
})

test("seção 06 lista só campanhas abertas e remete as encerradas ao histórico de postagens", async () => {
  const planner = await readFile(new URL("../src/components/campaigns/CampaignPlanner.tsx", import.meta.url), "utf8")
  assert.match(planner, /\["preparing", "active", "paused"\]\.includes\(record\.lifecycle\)/)
  assert.match(planner, /openCampaigns\.map\(\(record\)/)
  assert.match(planner, /Nenhuma campanha ativa neste perfil/)
  assert.match(planner, /só no histórico de postagens/)
})
