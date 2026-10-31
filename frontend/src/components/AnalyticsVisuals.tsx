import { useId } from 'react'
import { Activity, AlertCircle, CheckCircle2, CircleHelp, Gauge, TrendingUp } from 'lucide-react'
import { Panel } from './ui/Panel'
import '../styles/analytics-panels.css'

export type AnalyticsNetwork = 'threads' | 'facebook' | 'instagram' | 'tiktok' | 'x'
export type AnalyticsSummaryRow = {
  network: AnalyticsNetwork
  succeeded: number
  failed: number
  unknown: number
  views: number | null
  insights_status: string
}
export type AnalyticsTimeline = {
  days: number
  points: { day: string; network: AnalyticsNetwork; status: 'succeeded' | 'failed' | 'unknown'; total: number }[]
}

const networkNames: Record<AnalyticsNetwork, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}
const networkColors: Record<AnalyticsNetwork, string> = {
  threads: 'var(--brand-electric-cyan)',
  facebook: 'var(--brand-orbit-blue)',
  instagram: 'var(--brand-orbital-violet)',
  tiktok: 'var(--brand-indigo)',
  x: 'var(--brand-ice-blue)',
}
const statusColors = {
  succeeded: 'var(--positive)',
  failed: 'var(--negative)',
  unknown: 'var(--amber-300)',
}
const formatNumber = (value: number) => value.toLocaleString('pt-BR')
const shortDate = (date: string) => date.slice(8, 10) + '/' + date.slice(5, 7)

function RadialBreakdown({ items, center, sublabel, accessibleLabel }: {
  items: { label: string; value: number; color: string; tone: string }[]
  center: string
  sublabel: string
  accessibleLabel: string
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0)
  let offset = 0
  return <div className="analytics-radial-layout">
    <svg viewBox="0 0 184 184" className="analytics-radial" role="img" aria-label={accessibleLabel}>
      <circle cx="92" cy="92" r="70" fill="none" stroke="var(--chart-grid)" strokeWidth="16" />
      {total > 0 && items.filter(item => item.value > 0).map(item => {
        const length = (item.value / total) * 100
        const start = offset
        offset += length
        return <circle key={item.label} cx="92" cy="92" r="70" fill="none" stroke={item.color}
          strokeWidth="16" pathLength="100" strokeDasharray={String(length) + ' ' + String(100 - length)}
          strokeDashoffset={String(-start)} transform="rotate(-90 92 92)">
          <title>{item.label}: {formatNumber(item.value)}</title>
        </circle>
      })}
      <text x="92" y="88" textAnchor="middle" className="analytics-radial-value">{center}</text>
      <text x="92" y="108" textAnchor="middle" className="analytics-radial-caption">{sublabel}</text>
    </svg>
    <ul className="analytics-radial-legend">
      {items.map(item => <li key={item.label}>
        <span className="analytics-legend-name"><span className={'analytics-legend-dot analytics-legend-' + item.tone} />{item.label}</span>
        <strong>{formatNumber(item.value)}</strong>
      </li>)}
    </ul>
  </div>
}

function PublicationTrend({ timeline, days, loading, error }: {
  timeline?: AnalyticsTimeline
  days: number
  loading: boolean
  error: boolean
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
      <svg viewBox="0 0 680 256" className="analytics-timeline-chart" role="img"
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
  ok: 'Coleta confirmada',
  no_data: 'Sem períodos retornados',
  not_connected: 'Rede não conectada',
  api_error: 'API não autorizou a leitura',
  network_error: 'Falha de conexão',
  invalid_response: 'Resposta não validada',
  not_collected: 'Aguardando coleta',
  unsupported: 'Métrica não disponível',
}

export function AnalyticsVisuals({ rows, days, timeline, timelineLoading, timelineError }: {
  rows: AnalyticsSummaryRow[]
  days: number
  timeline?: AnalyticsTimeline
  timelineLoading: boolean
  timelineError: boolean
}) {
  const completed = rows.reduce((sum, row) => sum + row.succeeded, 0)
  const failed = rows.reduce((sum, row) => sum + row.failed, 0)
  const uncertain = rows.reduce((sum, row) => sum + row.unknown, 0)
  const all = completed + failed + uncertain
  const confirmedRate = all > 0 ? Math.round(completed / all * 100) : null
  const views = rows.filter(row => row.network === 'facebook' && row.views !== null)
  const firstViews = views.length ? views[0].views : null
  return <div className="analytics-visuals">
    <section className="analytics-kpi-grid" aria-label="Resumo dos envios">
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-primary">
        <div className="analytics-kpi-top"><span>Envios concluídos</span><CheckCircle2 size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(completed)}</strong>
        <small>Publicações confirmadas</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-failed">
        <div className="analytics-kpi-top"><span>Falhas</span><AlertCircle size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(failed)}</strong>
        <small>Envios com erro registrado</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-unknown">
        <div className="analytics-kpi-top"><span>Sem confirmação</span><CircleHelp size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{formatNumber(uncertain)}</strong>
        <small>Exigem verificação na rede</small>
      </Panel>
      <Panel surface="dark" className="analytics-kpi-card analytics-kpi-rate">
        <div className="analytics-kpi-top"><span>Taxa confirmada</span><Gauge size={20} aria-hidden="true" /></div>
        <strong className="analytics-kpi-value">{confirmedRate === null ? '—' : String(confirmedRate) + '%'}</strong>
        <small>{all > 0 ? formatNumber(completed) + ' de ' + formatNumber(all) + ' envios' : 'Sem envios para calcular'}</small>
      </Panel>
    </section>

    <div className="analytics-dashboard-grid">
      <Panel surface="dark" className="analytics-data-panel analytics-trend-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><TrendingUp size={14} aria-hidden="true" /> DESEMPENHO</span>
            <h2>Evolução das publicações</h2><p>Atividade diária no período selecionado</p></div>
          <span className="analytics-panel-period">{days} dias</span>
        </div>
        <PublicationTrend timeline={timeline} days={days} loading={timelineLoading} error={timelineError} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-network-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><Activity size={14} aria-hidden="true" /> REDES SOCIAIS</span>
            <h2>Envios por rede</h2><p>Distribuição dos envios concluídos</p></div>
        </div>
        <RadialBreakdown
          items={rows.map(row => ({ label: networkNames[row.network], value: row.succeeded, color: networkColors[row.network], tone: row.network }))}
          center={formatNumber(completed)} sublabel="concluídos"
          accessibleLabel={'Distribuição de ' + completed + ' publicações concluídas entre as redes selecionadas.'} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-status-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><Gauge size={14} aria-hidden="true" /> RESULTADOS</span>
            <h2>Situação dos envios</h2><p>O que ocorreu com as publicações</p></div>
        </div>
        <RadialBreakdown
          items={[
            { label: 'Concluídos', value: completed, color: statusColors.succeeded, tone: 'succeeded' },
            { label: 'Falhas', value: failed, color: statusColors.failed, tone: 'failed' },
            { label: 'Sem confirmação', value: uncertain, color: statusColors.unknown, tone: 'unknown' },
          ]}
          center={formatNumber(all)} sublabel="envios"
          accessibleLabel={'Situação: ' + completed + ' concluídos, ' + failed + ' falhas e ' + uncertain + ' sem confirmação.'} />
      </Panel>
      <Panel surface="dark" className="analytics-data-panel analytics-insights-panel">
        <div className="analytics-panel-heading">
          <div><span className="analytics-panel-eyebrow"><Activity size={14} aria-hidden="true" /> DADOS OFICIAIS</span>
            <h2>Insights das plataformas</h2><p>Disponibilidade da última coleta</p></div>
        </div>
        {firstViews !== null && <div className="analytics-insights-highlight">
          <span>Visualizações da Página do Facebook</span>
          <strong>{formatNumber(firstViews!)}</strong>
          <small>Somente períodos fornecidos pela Meta; não são visualizações individuais dos posts.</small>
        </div>}
        <ul className="analytics-insights-list">
          {rows.map(row => <li key={row.network}>
            <span>{networkNames[row.network]}</span>
            <span className={'analytics-insights-status ' + (row.insights_status === 'ok' ? 'is-available' : '')}>
              <span className="analytics-insights-indicator" />
              {providerDescriptions[row.insights_status] ?? 'Consulta não disponível'}
            </span>
          </li>)}
        </ul>
        <p className="analytics-insights-note">Uma métrica indisponível não equivale a zero. As fontes e os valores detalhados permanecem na tabela abaixo.</p>
      </Panel>
    </div>
  </div>
}
