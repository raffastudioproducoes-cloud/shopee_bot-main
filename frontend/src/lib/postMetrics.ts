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

/** Colunas da tabela por post: as do ranking mais alcance e salvamentos (Instagram/Facebook). */
export const TABLE_METRICS = ['views', 'reach', 'likes', 'comments', 'shares', 'saves', 'clicks'] as const
export type TableMetric = typeof TABLE_METRICS[number]
export const TABLE_LABELS: Record<TableMetric, string> = {
  ...METRIC_LABELS, reach: 'Alcance', saves: 'Salvamentos',
}

/** Coluna extra, só exibida quando alguma linha tem o valor (Reels/vídeo Meta). */
export const WATCH_TIME_LABEL = 'Tempo médio assistido'
export const WATCH_TIME_NOTE = 'Tempo médio de reprodução por visualização (Reels/vídeo)'

/** Milissegundos em segundos legíveis ("4,5 s", "1 min 05 s"); ausente = "—". */
export function formatWatchTime(ms: unknown): string {
  if (typeof ms !== 'number' || !Number.isFinite(ms) || ms < 0) return '—'
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s`
  const whole = Math.round(seconds)
  return `${Math.floor(whole / 60)} min ${String(whole % 60).padStart(2, '0')} s`
}

export function hasWatchTime(rows: { avg_watch_time_ms?: number | null }[]): boolean {
  return rows.some((row) => typeof row.avg_watch_time_ms === 'number')
}

/** O que cada coluna significa em cada rede (tooltip da célula). Ausente = rótulo genérico. */
const NETWORK_METRIC_NOTES: Record<string, Partial<Record<TableMetric, string>>> = {
  threads: { shares: 'Compartilhamentos + reposts' },
  instagram: { views: 'Visualizações da mídia', reach: 'Contas alcançadas', saves: 'Salvamentos', shares: 'Compartilhamentos + reposts' },
  facebook: { views: 'Visualizações de mídia do post', reach: 'Pessoas que viram a mídia', likes: 'Reações (todos os tipos)' },
}

export function metricNote(network: string, metric: TableMetric): string {
  return NETWORK_METRIC_NOTES[network]?.[metric] ?? TABLE_LABELS[metric]
}

/** Estado da coleta de um post em texto para o usuário; null quando não há o que avisar. */
const RECONNECT = 'Reconecte a conta para liberar insights'
export const ACCESS_DENIED = 'A Meta recusou os insights deste post (a Página pode ter menos de 100 curtidas ou faltar permissão). Veja o código no log.'
const STATUS_NOTES: Record<string, string> = {
  parcial: 'Sequência: métricas só da última parte',
  sem_id: 'ID do post na rede não localizado',
  permission_required: RECONNECT,
  token_expired: RECONNECT,
  access_denied: ACCESS_DENIED,
  not_found: 'Post removido ou indisponível na rede',
  unsupported_type: 'Vídeo do Facebook: métricas por vídeo ainda não coletadas',
  rate_limited: 'Limite da API atingido; nova tentativa na próxima coleta',
  api_error: 'A rede não respondeu às métricas deste post',
  network_error: 'Falha de conexão na última coleta',
  no_data: 'A rede ainda não devolveu dados (Instagram pode atrasar até 48 h)',
}

/** Página com menos de 100 curtidas: a Meta não libera insights. N vem da última coleta (null = desconhecido). */
export const MIN_PAGE_FANS = 100
export function audienceNote(fanCount?: number | null): string {
  const base = `A Meta só libera insights de Páginas com ${MIN_PAGE_FANS} curtidas ou mais.`
  return typeof fanCount === 'number' && Number.isFinite(fanCount)
    ? `${base} Esta Página tem ${fanCount.toLocaleString('pt-BR')}.` : base
}

export function collectionNote(status: string, fanCount?: number | null): string | null {
  if (status === 'audience_below_minimum') return audienceNote(fanCount)
  return STATUS_NOTES[status] ?? null
}

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
