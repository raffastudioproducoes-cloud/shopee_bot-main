import { useCountProgress } from '../lib/motion'
import { useId } from 'react'
import { Activity, BarChart3, Eye, Gauge, Layers, MessageCircle, TrendingUp } from 'lucide-react'
import { Panel } from './ui/Panel'
import { buildAdminDiagnosticSections } from '../lib/credentialPlatforms'
import '../styles/analytics-panels.css'

export type AnalyticsNetwork = 'threads' | 'facebook' | 'instagram' | 'tiktok' | 'x'
export type AnalyticsSummaryRow = {
  network: AnalyticsNetwork
  succeeded: number
  failed: number
  unknown: number
  views: number | null
  likes: number | null
  comments: number | null
  reposts: number | null
  clicks: number | null
  posts_with_insights?: number
  posts_with_external_id?: number
  insights_status: string
}
export type AnalyticsTimeline = {
  days: number
  points: { day: string; network: AnalyticsNetwork; status: 'succeeded' | 'failed' | 'unknown'; total: number }[]
}

const networkNames: Record<AnalyticsNetwork, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}
const socialCatalog = buildAdminDiagnosticSections().social
export type AnalyticsPostMetric = {
  job_id: string
  network: AnalyticsNetwork
  preview: string
  finished_at: string
  state: string
  views: number | null
  likes: number | null
  comments: number | null
  reposts: number | null
  clicks: number | null
}
const formatNumber = (value: number) => value.toLocaleString('pt-BR')
/** Valor na fração `f` da animação de contagem (0→1), sempre inteiro. */
const counted = (value: number, f: number) => Math.round(value * f)
const shortDate = (date: string) => date.slice(8, 10) + '/' + date.slice(5, 7)

function RadialBreakdown({ items, center, sublabel, accessibleLabel, f }: {
  items: { label: string; value: number | null; color: string; tone: string }[]
  center: string
  sublabel: string
  accessibleLabel: string
  f: number
}) {
  const total = items.reduce((sum, item) => sum + (item.value ?? 0), 0)
  let offset = 0
  return <div className="analytics-radial-layout">
    <svg viewBox="0 0 184 184" className="analytics-radial" role="img" aria-label={accessibleLabel}>
      <circle cx="92" cy="92" r="70" fill="none" stroke="var(--chart-grid)" strokeWidth="16" />
      {total > 0 && items.filter(item => (item.value ?? 0) > 0).map(item => {
        const length = ((item.value ?? 0) / total) * 100 * f
        const start = offset
        offset += length
        return <circle key={item.label} cx="92" cy="92" r="70" fill="none" stroke={item.color}
          strokeWidth="16" pathLength="100" strokeDasharray={String(length) + ' ' + String(100 - length)}
          strokeDashoffset={String(-start)} transform="rotate(-90 92 92)">
          <title>{item.label}: {formatNumber(item.value ?? 0)}</title>
        </circle>
      })}
      <text x="92" y="88" textAnchor="middle" className="analytics-radial-value">{center}</text>
      <text x="92" y="108" textAnchor="middle" className="analytics-radial-caption">{sublabel}</text>
    </svg>
    <ul className="analytics-radial-legend">
      {items.map(item => <li key={item.label}>
        <span className="analytics-legend-name"><span className={'analytics-legend-dot analytics-legend-' + item.tone} />{item.label}</span>
        <strong>{item.value === null ? '—' : formatNumber(counted(item.value, f))}</strong>
      </li>)}
    </ul>
  </div>
}

function PublicationTrend({ timeline, days, loading, error, f }: {
  timeline?: AnalyticsTimeline
  days: number
  loading: boolean
  error: boolean
  f: number
}) {
  const gradientId = 'analyticsArea' + useId().replace(/:/g, '')
  const today = new Date()
  const midnightUTC = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  // Janela móvel de N×24h pode atravessar N+1 datas UTC.
  const dates = Array.from({ length: days + 1 }, (_, index) =>
    new Date(midnightUTC - (days - index) * 86400000).toISOString().slice(0, 10))
  const counts = new Map<string, number>()
  for (const point of timeline?.points ?? []) {
    if (!dates.includes(point.day) || !['succeeded', 'failed', 'unknown'].includes(point.status)) continue
    const key = point.day + ':' + point.status
    counts.set(key, (counts.get(key) ?? 0) + point.total)
  }
  const values = (status: 'succeeded' | 'failed' | 'unknown') =>
    dates.map(day => counts.get(day + ':' + status) ?? 0)
  const series = {
    succeeded: values('succeeded'), failed: values('failed'), unknown: values('unknown'),
  }
  const allValues = [...series.succeeded, ...series.failed, ...series.unknown]
  const maximum = Math.max(4, ...allValues)
  const xStart = 46
  const xEnd = 644
  const yTop = 24
  const yBottom = 208
  const xAt = (index: number) => xStart + index * (xEnd - xStart) / (dates.length - 1)
  const yAt = (value: number) => yBottom - value / maximum * (yBottom - yTop)
  const line = (v: number[]) => v.map((value, index) =>
    (index === 0 ? 'M' : 'L') + xAt(index).toFixed(2) + ',' + yAt(value).toFixed(2)).join(' ')
  const successLine = line(series.succeeded)
  const area = successLine + ' L' + xEnd + ',' + yBottom + ' L' + xStart + ',' + yBottom + ' Z'
  const hasActivity = allValues.some(value => value > 0)
  const middle = Math.floor(dates.length / 2)
  return <>
    <div className="analytics-chart-legend">
      <span><i className="analytics-legend-dot analytics-dot-success" />Concluídos</span>
      <span><i className="analytics-legend-dot analytics-dot-failure" />Falhas</span>
      <span><i className="analytics-legend-dot analytics-dot-unknown" />Sem confirmação</span>
    </div>
    <div className="analytics-chart-container">
      {loading ? <p className="analytics-chart-message" role="status">Carregando histórico...</p>
        : error ? <p className="analytics-chart-message" role="alert">Evolução indisponível nesta consulta.</p>
          : !hasActivity ? <p className="analytics-chart-message">Sem publicações finalizadas no período selecionado.</p> : null}
      <svg viewBox="0 0 680 256" className="analytics-timeline-chart" role="img" style={f < 1 ? { clipPath: `inset(0 ${(1 - f) * 100}% 0 0)` } : undefined}
        aria-label={'Evolução diária, UTC, de publicações nos últimos ' + days + ' dias. ' +
          'Concluídos, falhas e sem confirmação representados pelas linhas.'}>
        <defs><linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--brand-electric-cyan)" stopOpacity=".20" />
          <stop offset="100%" stopColor="var(--brand-electric-cyan)" stopOpacity="0" />
        </linearGradient></defs>
        {[0, 1, 2, 3, 4].map(index => {
          const v = maximum * (1 - index / 4)
          const y = yAt(v)
          return <g key={index}>
            <line x1={xStart} y1={y} x2={xEnd} y2={y} className="analytics-chart-gridline" />
            <text x="37" y={y + 4} textAnchor="end" className="analytics-chart-axis">{formatNumber(Math.round(v))}</text>
          </g>
        })}
        {[0, middle, dates.length - 1].map(index => <text key={index} x={xAt(index)} y="242"
          textAnchor={index === 0 ? 'start' : index === dates.length - 1 ? 'end' : 'middle'}
          className="analytics-chart-axis">{shortDate(dates[index])}</text>)}
        {hasActivity && <>
          <path d={area} fill={'url(#' + gradientId + ')'} />
          <path d={successLine} className="analytics-chart-line-success" />
          {series.failed.some(value => value > 0) && <path d={line(series.failed)} className="analytics-chart-line-failure" />}
          {series.unknown.some(value => value > 0) && <path d={line(series.unknown)} className="analytics-chart-line-unknown" />}
          {series.succeeded.map((value, index) => value > 0 ? <circle key={index}
            cx={xAt(index)} cy={yAt(value)} r="3.1" className="analytics-chart-point">
            <title>{shortDate(dates[index])} UTC: {formatNumber(value)} concluído(s)</title>
          </circle> : null)}
        </>}
      </svg>
    </div>
    <p className="analytics-chart-footnote">Envios finalizados por dia (UTC), registrados pelo Auto Orbital. O período usa uma janela móvel de {days} dias.</p>
  </>
}

const providerDescriptions: Record<string, string> = {
  ok: 'Insights dos posts coletados',
  partial: 'Coleta parcial dos posts',
  no_data: 'Post sem dados retornados',
  no_posts: 'Sem posts confirmados',
  missing_external_id: 'Post sem ID rastreável',
  multipart_unmapped: 'Sequência de posts incompleta',
  not_connected: 'Rede não conectada',
  api_error: 'API não retornou insights do post',
  permission_required: 'Sem permissão para insights do post',
  network_error: 'Falha de conexão',
  invalid_response: 'Resposta não validada',
  not_collected: 'Aguardando coleta',
  unsupported: 'Insights por post indisponíveis',
}

function NetworkComparison({ rows, f }: { rows: AnalyticsSummaryRow[]; f: number }) {
  const source = new Map(rows.map(row => [row.network, row]))
  const maximum = Math.max(1, ...rows.map(row => row.succeeded + row.failed + row.unknown))
  return <>
    <div className="analytics-chart-legend">
      <span><i className="analytics-legend-dot analytics-legend-succeeded" />Concluídos</span>
      <span><i className="analytics-legend-dot analytics-legend-failed" />Falhas</span>
      <span><i className="analytics-legend-dot analytics-legend-unknown" />Sem confirmação</span>
    </div>
    <svg className="analytics-comparison-chart" viewBox="0 0 670 326" role="img"
      aria-label="Comparação de envios finalizados por rede social, sem incluir as redes indisponíveis">
      {socialCatalog.map((channel, index) => {
        const row = source.get(channel.key as AnalyticsNetwork)
        const total = row ? row.succeeded + row.failed + row.unknown : 0
        const y = index * 35 + 19
        const bars = row ? [
          { value: row.succeeded, color: 'var(--positive)' },
          { value: row.failed, color: 'var(--negative)' },
          { value: row.unknown, color: 'var(--amber-300)' },
        ] : []
        let offset = 0
        return <g key={channel.key}>
          <text x="4" y={y + 9} className={'analytics-bar-name' + (!row ? ' analytics-muted' : '')}>{channel.title}</text>
          <rect x="150" y={y - 1} width="424" height="12" rx="5" fill="var(--chart-grid)" />
          {bars.map(({ value, color }, segment) => {
            const width = (value / maximum) * 424 * f
            const x = 150 + offset
            offset += width
            return value > 0 ? <rect key={segment} x={x} y={y - 1} width={width} height="12" fill={color}>
              <title>{channel.title}: {formatNumber(value)} {['concluídos', 'falhas', 'sem confirmação'][segment]}</title>
            </rect> : null
          })}
          <text x="644" y={y + 9} textAnchor="end" className="analytics-bar-count">
            {row ? formatNumber(counted(total, f)) : '—'}
          </text>
        </g>
      })}
    </svg>
    <p className="analytics-chart-footnote">Somente envios registrados na plataforma; — indica rede sem dados neste filtro ou sem publicação disponível.</p>
  </>
}

function WeekdayActivity({ timeline, loading, error, f }: { timeline?: AnalyticsTimeline; loading: boolean; error: boolean; f: number }) {
  const labels = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
  const totals = Array(7).fill(0) as number[]
  for (const point of timeline?.points ?? []) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(point.day)) continue
    const date = new Date(point.day + 'T00:00:00Z')
    const index = (date.getUTCDay() + 6) % 7
    totals[index] += point.total
  }
  const max = Math.max(1, ...totals)
  return <>
    {loading ? <p className="analytics-chart-note">Carregando distribuição semanal...</p>
      : error ? <p role="alert" className="analytics-chart-note">Distribuição semanal indisponível.</p>
        : totals.every(value => value === 0) ? <p className="analytics-chart-note">Sem atividade registrada no período.</p> : null}
    <svg viewBox="0 0 560 212" className="analytics-weekday-chart" role="img" aria-label="Quantidade de envios por dia da semana em UTC">
      {totals.map((count, index) => {
        const h = count / max * 142 * f
        return <g key={labels[index]}>
          <rect x={24 + index * 78} y={25} width="46" height="142" rx="8" fill="var(--chart-grid)" />
          {count > 0 && <rect x={24 + index * 78} y={167 - h} width="46" height={h} rx="8" fill="var(--brand-electric-cyan)" />}
          <text x={47 + index * 78} y="20" textAnchor="middle" className="analytics-bar-count">{counted(count, f)}</text>
          <text x={47 + index * 78} y="193" textAnchor="middle" className="analytics-bar-name">{labels[index]}</text>
        </g>
      })}
    </svg>
    <p className="analytics-chart-footnote">Frequência dos envios finalizados por dia da semana (UTC), não previsão de alcance.</p>
  </>
}

function SocialAvailability({ rows }: { rows: AnalyticsSummaryRow[] }) {
  const status = new Map(rows.map(row => [row.network, row]))
  return <div className="analytics-social-grid" aria-label="Situação das nove redes sociais">
    {socialCatalog.map(channel => {
      const row = status.get(channel.key as AnalyticsNetwork)
      const planned = channel.availability === 'planned'
      return <div className={'analytics-social-item' + (planned ? ' is-planned' : '')} key={channel.key}>
        <strong>{channel.title}</strong>
        <span className={'analytics-insights-status' + (row?.insights_status === 'ok' ? ' is-available' : '')}>
          <i className="analytics-insights-indicator" />
          {planned ? 'Em breve · sem integração' : !row && channel.key === 'kwai' ? 'Insights por post indisponíveis'
            : !row ? 'Fora do filtro atual'
            : providerDescriptions[row.insights_status] ?? 'Sem coleta oficial'}
        </span>
        {row && [row.views, row.likes, row.comments, row.reposts, row.clicks].some(value => value !== null) &&
          <div className="analytics-social-metrics" aria-label={`Métricas oficiais de ${channel.title}`}>
            {([
              ['Visualizações', row.views], ['Curtidas', row.likes], ['Comentários', row.comments],
              ['Reposts', row.reposts], ['Cliques', row.clicks],
            ] as const).map(([label, value]) => (
              <span key={label} title={label}>{label}: <strong>{value === null ? '—' : formatNumber(value)}</strong></span>
            ))}
          </div>}
      </div>
    })}
  </div>
}

function TopPosts({ posts, loading, error }: { posts?: AnalyticsPostMetric[]; loading: boolean; error: boolean }) {
  if (loading) return <p className="analytics-chart-note" role="status">Carregando desempenho por publicação...</p>
  if (error) return <p className="analytics-chart-note" role="alert">Ranking de publicações indisponível.</p>
  const ranked = [...(posts ?? [])].sort((a, b) => {
    if (a.views === null) return b.views === null ? b.finished_at.localeCompare(a.finished_at) : 1
    if (b.views === null) return -1
    return b.views - a.views || b.finished_at.localeCompare(a.finished_at)
  }).slice(0, 5)
  if (!ranked.length) return <p className="analytics-chart-note">Nenhuma publicação confirmada neste período.</p>
  const collectionLabel = (state: string) => state === 'ok' ? 'Coletado'
    : state === 'multipart_unmapped' ? 'Sequência sem IDs completos'
      : state === 'not_collected' ? 'Aguardando coleta'
        : state === 'missing_external_id' ? 'Sem ID da publicação'
          : 'Insights indisponíveis'
  return <>
    <ol className="analytics-top-posts">
      {ranked.map(post => <li key={post.job_id}>
        <div className="analytics-post-content">
          <strong>{post.preview || 'Publicação sem texto'}</strong>
          <small className="analytics-post-source">{networkNames[post.network]} · {new Date(post.finished_at).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' })} · {collectionLabel(post.state)}</small>
          <div className="analytics-post-metrics" aria-label="Interações oficiais da publicação">
            {([
              ['Curtidas', post.likes], ['Comentários', post.comments],
              ['Reposts', post.reposts], ['Cliques', post.clicks],
            ] as const).map(([label, value]) => <span key={label}>{label}: <strong>{value === null ? '—' : formatNumber(value)}</strong></span>)}
          </div>
        </div>
        <span className="analytics-post-views" title="Visualizações oficiais do post">
          <Eye size={14} aria-hidden="true" />{post.views === null ? '—' : formatNumber(post.views)}
        </span>
      </li>)}
    </ol>
    <p className="analytics-chart-footnote">Até cinco publicações ordenadas por visualizações oficiais; posts sem essa métrica aparecem ao final. — significa indisponível, não zero.</p>
  </>
}

export function AnalyticsVisuals({ rows, days, timeline, timelineLoading, timelineError, posts, postsLoading, postsError }: {
  rows: AnalyticsSummaryRow[]
  days: number
  timeline?: AnalyticsTimeline
  timelineLoading: boolean
  timelineError: boolean
  posts?: AnalyticsPostMetric[]
  postsLoading: boolean
  postsError: boolean
}) {
  const f = useCountProgress('analises')
  const completed = rows.reduce((sum, row) => sum + row.succeeded, 0)
  const failed = rows.reduce((sum, row) => sum + row.failed, 0)
  const uncertain = rows.reduce((sum, row) => sum + row.unknown, 0)
  const all = completed + failed + uncertain
  const confirmedRate = all > 0 ? Math.round(completed / all * 100) : null
  const networksWithActivity = rows.filter(row => row.succeeded + row.failed + row.unknown > 0).length
  const views = rows.filter(row => row.views !== null)
  const totalViews = views.length ? views.reduce((sum, row) => sum + row.views!, 0) : null
  const measured = (['likes', 'comments', 'reposts', 'clicks'] as const).map(key => {
    const known = rows.filter(row => row[key] !== null)
    return { key, value: known.length ? known.reduce((sum, row) => sum + row[key]!, 0) : null }
  })
  const measuredInteractions = measured.filter(item => item.value !== null)
  const interactionTotal = measuredInteractions.length
    ? measuredInteractions.reduce((sum, item) => sum + item.value!, 0) : null
  const postsWithInsights = rows.reduce((sum, row) => sum + (row.posts_with_insights ?? 0), 0)
  const postsWithExternalId = rows.reduce((sum, row) => sum + (row.posts_with_external_id ?? 0), 0)
  const engagementLabels: Record<string, string> = { likes: 'Curtidas', comments: 'Comentários', reposts: 'Reposts', clicks: 'Cliques' }
  const engagementColors = ['var(--brand-electric-cyan)', 'var(--brand-orbital-violet)', 'var(--positive)', 'var(--brand-ice-blue)']
  return <div className="analytics-visuals">
    <section className="analytics-kpi-grid" aria-label="Indicadores gerais e oficiais">
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-primary">
        <div className="analytics-kpi-top"><span>Total de envios</span><Layers size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(counted(all, f))}</strong>
        <small>{formatNumber(completed)} concluídos · {formatNumber(failed)} falhas · {formatNumber(uncertain)} sem confirmação</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-rate">
        <div className="analytics-kpi-top"><span>Taxa confirmada</span><Gauge size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{confirmedRate === null ? '—' : String(counted(confirmedRate, f)) + '%'}</strong>
        <small>{all > 0 ? `${formatNumber(completed)} de ${formatNumber(all)} envios` : 'Sem envios para calcular'}</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-networks">
        <div className="analytics-kpi-top"><span>Redes com atividade</span><BarChart3 size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(counted(networksWithActivity, f))}</strong>
        <small>De {socialCatalog.length} redes listadas</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-views">
        <div className="analytics-kpi-top"><span>Visualizações de posts</span><Eye size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{totalViews === null ? '—' : formatNumber(counted(totalViews, f))}</strong>
        <small>Somente dados oficiais dos posts rastreados</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-engagement">
        <div className="analytics-kpi-top"><span>Interações mensuradas</span><MessageCircle size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{interactionTotal === null ? '—' : formatNumber(counted(interactionTotal, f))}</strong>
        <small>Curtidas, comentários, reposts e cliques disponíveis</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-tracked">
        <div className="analytics-kpi-top"><span>Posts com insights</span><Activity size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(counted(postsWithInsights, f))}</strong>
        <small>{formatNumber(postsWithExternalId)} com ID rastreável</small>
      </Panel>
    </section>

    <div className="analytics-dashboard-grid">
      <Panel surface="dark" className="analytics-data-panel analytics-trend-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><TrendingUp size={14} aria-hidden="true" /> DESEMPENHO</span>
            <h2>Evolução das publicações</h2><p>Atividade diária no período selecionado</p></div>
          <span className="analytics-panel-period">{days} dias</span>
        </div>
        <PublicationTrend timeline={timeline} days={days} loading={timelineLoading} error={timelineError} f={f} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-network-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><BarChart3 size={14} aria-hidden="true" /> REDES SOCIAIS</span>
            <h2>Comparação entre redes</h2><p>Volume e resultados por plataforma</p></div>
        </div>
        <NetworkComparison rows={rows} f={f} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-status-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><MessageCircle size={14} aria-hidden="true" /> INTERAÇÕES</span>
            <h2>Composição do engajamento</h2><p>Tipos de interação oficialmente retornados por post</p></div>
        </div>
        <RadialBreakdown
          items={measured.map((item, index) => ({ label: engagementLabels[item.key] + (item.value === null ? ' (indisponível)' : ''),
            value: item.value, color: engagementColors[index], tone: item.key }))}
          center={interactionTotal === null ? '—' : formatNumber(counted(interactionTotal, f))} sublabel="interações" f={f}
          accessibleLabel="Interações de publicações rastreadas, agrupadas por curtidas, comentários, reposts e cliques." />
        <p className="analytics-chart-footnote">Dados indisponíveis não são contabilizados como zero. Apenas posts publicados pela plataforma.</p>
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-insights-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><BarChart3 size={14} aria-hidden="true" /> FREQUÊNCIA</span>
            <h2>Atividade por dia da semana</h2><p>Em quais dias os envios ocorreram</p></div>
        </div>
        <WeekdayActivity timeline={timeline} loading={timelineLoading} error={timelineError} f={f} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-top-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><Eye size={14} aria-hidden="true" /> CONTEÚDOS</span>
            <h2>Publicações em destaque</h2><p>Ranking e detalhes das publicações rastreadas</p></div>
        </div>
        <TopPosts posts={posts} loading={postsLoading} error={postsError} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-availability-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><Activity size={14} aria-hidden="true" /> INTEGRAÇÕES</span>
            <h2>Situação das redes</h2><p>Disponibilidade real da coleta por post</p></div>
        </div>
        <SocialAvailability rows={rows} />
        <p className="analytics-insights-note">Indicadores indisponíveis não equivalem a zero. Nenhuma métrica geral de perfis ou páginas é atribuída aos posts.</p>
      </Panel>
    </div>
  </div>
}
