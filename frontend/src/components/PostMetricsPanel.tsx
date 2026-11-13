import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { formatInstant } from '../lib/userTimeZone'
import {
  METRIC_LABELS, RANK_METRICS, UNAVAILABLE_TOOLTIP, formatMetric, seriesTotals,
  type RankMetric, type SeriesPoint,
} from '../lib/postMetrics'
import { Panel } from './ui/Panel'
import { Select } from './ui/Select'
import { Button } from './ui/Button'
import { SkeletonText } from './ui/Skeleton'
import '../styles/post-metrics.css'

const NETWORK_NAMES: Record<string, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}
const PAGE_SIZE = 25

export type PostMetricRow = {
  job_id: string
  network: string
  finished_at: string | null
  preview: string
  status: string
} & Record<RankMetric, number | null>
type ListResult = { posts: PostMetricRow[]; total: number; truncated: boolean }
type NetworkRank = { network: string; posts: number; posts_measured: number; total: number | null; average: number | null }
type RankingResult = { posts: PostMetricRow[]; networks: NetworkRank[] }
type SeriesResult = { points: SeriesPoint[]; clicks: { day: string; network: string; clicks: number }[] }

interface PostMetricsPanelProps {
  /** Query já validada: days/from/to/tz + rede e perfil. */
  query: string
  scopeKey: string
}

export function Metric({ value }: { value: number | null | undefined }) {
  const text = formatMetric(value)
  return text === '—' ? <span title={UNAVAILABLE_TOOLTIP} aria-label={UNAVAILABLE_TOOLTIP}>—</span> : <>{text}</>
}

function publishedAt(value: string | null) {
  return value ? formatInstant(value, { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

function EvolutionChart({ values }: { values: { day: string; value: number | null }[] }) {
  const known = values.filter((item) => item.value !== null)
  if (known.length < 2) return <p className="post-metrics-muted">Histórico insuficiente para a evolução (são necessárias ao menos duas coletas).</p>
  const max = Math.max(...known.map((item) => item.value as number), 1)
  const step = 600 / Math.max(values.length - 1, 1)
  const points = values.map((item, index) => item.value === null ? null : `${(index * step).toFixed(1)},${(170 - (item.value / max) * 160).toFixed(1)}`)
    .filter(Boolean).join(' ')
  const first = known[0]
  const last = known[known.length - 1]
  return <figure style={{ margin: 0 }}>
    <svg className="post-metrics-chart" viewBox="0 0 600 180" preserveAspectRatio="none" role="img"
      aria-label={`Evolução de ${formatMetric(first.value)} em ${first.day} para ${formatMetric(last.value)} em ${last.day}`}>
      <line x1="0" y1="170" x2="600" y2="170" />
      <polyline points={points} />
    </svg>
    <figcaption className="post-metrics-muted">{first.day} → {last.day} · máximo {formatMetric(max)}</figcaption>
  </figure>
}

export function PostMetricsPanel({ query, scopeKey }: PostMetricsPanelProps) {
  const [sort, setSort] = useState<RankMetric | 'finished_at'>('views')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(0)
  const [rankMetric, setRankMetric] = useState<RankMetric>('views')
  const [seriesMetric, setSeriesMetric] = useState<RankMetric>('views')

  const list = useQuery({
    queryKey: ['post-metrics', scopeKey, query, sort, order, page],
    queryFn: () => api.get<ListResult>(`/analytics/post-metrics?${query}&sort=${sort}&order=${order}&limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`),
  })
  const ranking = useQuery({
    queryKey: ['post-ranking', scopeKey, query, rankMetric],
    queryFn: () => api.get<RankingResult>(`/analytics/ranking?${query}&metric=${rankMetric}&top=10`),
  })
  const series = useQuery({
    queryKey: ['post-series', scopeKey, query],
    queryFn: () => api.get<SeriesResult>(`/analytics/series?${query}`),
  })

  function toggleSort(field: RankMetric | 'finished_at') {
    setPage(0)
    if (field === sort) setOrder(order === 'desc' ? 'asc' : 'desc')
    else { setSort(field); setOrder('desc') }
  }

  const evolution = seriesMetric === 'clicks'
    ? seriesTotals((series.data?.clicks ?? []).map((item) => ({ day: item.day, network: item.network, clicks: item.clicks })), 'clicks')
    : seriesTotals(series.data?.points ?? [], seriesMetric)
  const rows = list.data?.posts ?? []
  const total = list.data?.total ?? 0
  const metricOptions = RANK_METRICS.map((key) => ({ value: key, label: METRIC_LABELS[key] }))

  return <section className="post-metrics" aria-label="Métricas por postagem">
    <div className="post-metrics-grid">
      <Panel surface="glass" className="analytics-data-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow">RANKING</span><h2>Melhores posts</h2><p>Top 10 pela métrica escolhida; posts sem a métrica ficam de fora.</p></div>
          <Select label="Métrica" value={rankMetric} width={170} onChange={(event) => setRankMetric(event.target.value as RankMetric)} options={metricOptions} />
        </div>
        {ranking.isLoading ? <SkeletonText lines={3} />
          : ranking.isError ? <p role="alert">Ranking indisponível.</p>
            : !ranking.data?.posts.length ? <p className="post-metrics-muted">Nenhum post com {METRIC_LABELS[rankMetric].toLowerCase()} medido neste período.</p>
              : <ol className="post-metrics-list">{ranking.data.posts.map((post) => <li key={post.job_id}>
                <strong><Metric value={post[rankMetric]} /></strong> · {NETWORK_NAMES[post.network] ?? post.network} · {post.preview}
                <div className="post-metrics-muted">{publishedAt(post.finished_at)}</div>
              </li>)}</ol>}
      </Panel>
      <Panel surface="dark" className="analytics-data-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow">REDES</span><h2>Melhor rede</h2><p>{METRIC_LABELS[rankMetric]}: soma e média por post medido.</p></div>
        </div>
        {ranking.isLoading ? <SkeletonText lines={3} />
          : !ranking.data?.networks.length ? <p className="post-metrics-muted">Nenhuma publicação confirmada neste período.</p>
            : <table className="post-metrics-table"><thead><tr><th>Rede</th><th>Soma</th><th>Média/post</th><th>Posts medidos</th></tr></thead>
              <tbody>{ranking.data.networks.map((item) => <tr key={item.network}>
                <td>{NETWORK_NAMES[item.network] ?? item.network}</td>
                <td><Metric value={item.total} /></td><td><Metric value={item.average} /></td>
                <td>{item.posts_measured} de {item.posts}</td>
              </tr>)}</tbody></table>}
      </Panel>
    </div>

    <Panel surface="dark" className="analytics-data-panel">
      <div className="analytics-panel-heading">
        <div><span className="analytics-panel-eyebrow">HISTÓRICO</span><h2>Evolução</h2>
          <p>{seriesMetric === 'clicks' ? 'Cliques por dia no link rastreado.' : 'Total acumulado dos posts por dia, a partir das coletas guardadas.'}</p></div>
        <Select label="Métrica" value={seriesMetric} width={170} onChange={(event) => setSeriesMetric(event.target.value as RankMetric)} options={metricOptions} />
      </div>
      {series.isLoading ? <SkeletonText lines={3} />
        : series.isError ? <p role="alert">Histórico indisponível.</p>
          : <EvolutionChart values={evolution} />}
    </Panel>

    <Panel surface="glass" className="analytics-data-panel">
      <div className="analytics-panel-heading">
        <div><span className="analytics-panel-eyebrow">POR POSTAGEM</span><h2>Desempenho de cada post</h2>
          <p>Totais acumulados até a última coleta. "—" = a rede não fornece a métrica. Cliques contam só links rastreados pelo Auto Orbital.</p></div>
      </div>
      {list.isLoading ? <SkeletonText lines={3} />
        : list.isError ? <p role="alert">Métricas por publicação indisponíveis.</p>
          : !rows.length ? <p className="post-metrics-muted">Nenhuma publicação confirmada neste período. Publique um post e aguarde a próxima coleta.</p>
            : <>
              <div className="post-metrics-table-wrap"><table className="post-metrics-table">
                <thead><tr>
                  <th scope="col">Post</th>
                  <th scope="col"><button type="button" aria-pressed={sort === 'finished_at'} onClick={() => toggleSort('finished_at')}>Publicado em</button></th>
                  {RANK_METRICS.map((key) => <th scope="col" key={key} aria-sort={sort === key ? (order === 'desc' ? 'descending' : 'ascending') : 'none'}>
                    <button type="button" aria-pressed={sort === key} onClick={() => toggleSort(key)}>
                      {METRIC_LABELS[key]}{sort === key ? (order === 'desc' ? ' ↓' : ' ↑') : ''}
                    </button></th>)}
                </tr></thead>
                <tbody>{rows.map((post) => <tr key={post.job_id}>
                  <td><strong>{NETWORK_NAMES[post.network] ?? post.network}</strong> · {post.preview}
                    {post.status === 'parcial' && <div className="post-metrics-muted">Sequência: métricas só da última parte</div>}
                    {post.status === 'sem_id' && <div className="post-metrics-muted">Confirmação manual sem ID localizado</div>}</td>
                  <td>{publishedAt(post.finished_at)}</td>
                  {RANK_METRICS.map((key) => <td key={key}><Metric value={post[key]} /></td>)}
                </tr>)}</tbody>
              </table></div>
              <div className="post-metrics-pager">
                <span className="post-metrics-muted">{page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} de {total}{list.data?.truncated ? ' (limite atingido)' : ''}</span>
                <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Anterior</Button>
                <Button variant="secondary" size="sm" disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage(page + 1)}>Próxima</Button>
              </div>
            </>}
    </Panel>
  </section>
}
