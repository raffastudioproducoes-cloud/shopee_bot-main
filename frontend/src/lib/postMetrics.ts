// Métricas por postagem: formatação, ordenação e período. Sem imports de propósito:
// os testes em node carregam este arquivo direto (ver tests/post-metrics.test.mjs).

export const PERIOD_OPTIONS = ['7', '30', '90', '180', '365', 'custom'] as const
export const LEGACY_PERIODS = ['7', '30', '90']
export const MAX_RANGE_DAYS = 365
export const RANK_METRICS = ['views', 'likes', 'comments', 'shares', 'clicks'] as const
export type RankMetric = typeof RANK_METRICS[number]
export const METRIC_LABELS: Record<RankMetric, string> = {
  views: 'Visualizações', likes: 'Curtidas', comments: 'Comentários',
  shares: 'Compart./reposts', clicks: 'Cliques',
}
export const UNAVAILABLE_TOOLTIP = 'a rede não fornece esta métrica'

/** Métrica indisponível é "—", nunca 0. */
export function formatMetric(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('pt-BR') : '—'
}

type Sortable = { finished_at?: string | null } & Record<string, unknown>

/** Nulos sempre no fim (mesma regra da API); empate pela publicação mais recente. */
export function sortByMetric<T extends Sortable>(rows: T[], field: string, descending = true): T[] {
  const value = (row: T) => (typeof row[field] === 'number' ? (row[field] as number) : null)
  const present = rows.filter((row) => value(row) !== null)
  const missing = rows.filter((row) => value(row) === null)
  const byDate = (a: T, b: T) => String(b.finished_at ?? '').localeCompare(String(a.finished_at ?? ''))
  present.sort((a, b) => {
    const diff = (value(a) as number) - (value(b) as number)
    return diff !== 0 ? (descending ? -diff : diff) : byDate(a, b)
  })
  return [...present, ...missing.sort(byDate)]
}

/** Dias inclusivos de um intervalo AAAA-MM-DD; null se inválido. */
export function rangeDays(from: string, to: string): number | null {
  const pattern = /^\d{4}-\d{2}-\d{2}$/
  if (!pattern.test(from) || !pattern.test(to)) return null
  const start = Date.parse(`${from}T00:00:00Z`)
  const end = Date.parse(`${to}T00:00:00Z`)
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null
  return Math.round((end - start) / 86400000) + 1
}

/** Mensagem de erro do intervalo personalizado, ou null quando válido. */
export function customRangeError(from: string, to: string): string | null {
  if (!from || !to) return 'Informe início e fim.'
  const days = rangeDays(from, to)
  if (days === null) return 'O fim deve ser igual ou posterior ao início.'
  if (days > MAX_RANGE_DAYS) return 'O intervalo máximo é de 365 dias.'
  return null
}

/** Query string do período (sem "&" inicial) ou null se o intervalo é inválido. */
export function periodQuery(period: string, from: string, to: string, tz: string): string | null {
  const zone = `tz=${encodeURIComponent(tz)}`
  if (period === 'custom') {
    return customRangeError(from, to) ? null : `from=${from}&to=${to}&${zone}`
  }
  return (PERIOD_OPTIONS as readonly string[]).includes(period) ? `days=${period}&${zone}` : null
}

export type SeriesPoint = { day: string; network: string } & Partial<Record<RankMetric, number | null>>

/** Soma das redes por dia para o gráfico de evolução; dia sem valor algum = null. */
export function seriesTotals(points: SeriesPoint[], metric: RankMetric): { day: string; value: number | null }[] {
  const byDay = new Map<string, number | null>()
  for (const point of points) {
    const value = point[metric]
    const current = byDay.get(point.day) ?? null
    byDay.set(point.day, typeof value === 'number' ? (current ?? 0) + value : current)
  }
  return [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([day, value]) => ({ day, value }))
}
