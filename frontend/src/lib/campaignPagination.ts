import type { CampaignProgress } from "../api/campaigns"

/** Itens por página na prévia e no histórico das campanhas. */
export const CAMPAIGN_PAGE_SIZE = 10

export function campaignPageCount(total: number, size = CAMPAIGN_PAGE_SIZE): number {
  return Math.max(1, Math.ceil(Math.max(0, total) / size))
}

export function clampCampaignPage(page: number, count: number): number {
  const safe = Number.isFinite(page) ? Math.trunc(page) : 1
  return Math.max(1, Math.min(safe, count))
}

/** Janela de páginas: primeira, última e vizinhas da atual; lacunas viram "…". */
export function campaignPageWindow(current: number, count: number): Array<number | "…"> {
  const wanted = new Set([1, count, current - 1, current, current + 1])
  const pages = [...wanted].filter((p) => p >= 1 && p <= count).sort((a, b) => a - b)
  const out: Array<number | "…"> = []
  pages.forEach((p, i) => {
    if (i > 0 && p - pages[i - 1] > 1) out.push("…")
    out.push(p)
  })
  return out
}

const COUNT_LABELS: Array<[keyof Omit<CampaignProgress, "total">, string]> = [
  ["planned", "planejados"], ["running", "em execução"], ["succeeded", "publicados"],
  ["failed", "falhas"], ["unknown", "incertos"], ["cancelled", "cancelados"],
]

/** Só os contadores relevantes (maiores que zero), na ordem do ciclo de vida. */
export function relevantProgressCounts(progress: CampaignProgress): Array<{ key: string; label: string; value: number }> {
  return COUNT_LABELS
    .map(([key, label]) => ({ key, label, value: progress[key] }))
    .filter((item) => item.value > 0)
}
