import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminMetricsApi } from '../api/adminMetrics'
import { Panel } from '../components/ui/Panel'
import { MetricTrend, PlanRings } from '../components/admin/MetricTrend'
import { SkeletonCard, SkeletonRegion } from '../components/ui/Skeleton'

const number = (value: number | null | undefined, suffix = '') => value == null ? 'Indisponível' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}${suffix}`
const status = { available: 'Conectado', partial: 'Dados parciais', unavailable: 'Indisponível', not_configured: 'Não configurado' }

export default function AdminOverviewPage() {
  const [days, setDays] = useState(30)
  const { data, isLoading, error } = useQuery({ queryKey: ['admin', 'metrics', days], queryFn: () => adminMetricsApi.get(days), refetchInterval: 60_000 })
  if (isLoading) return <SkeletonRegion><SkeletonCard /><SkeletonCard /></SkeletonRegion>
  if (error || !data) return <p role="alert">Não foi possível carregar as métricas administrativas.</p>
  const counts = data.counts
  const stats = [['Contas atuais', counts?.accounts], ['Ativos · últimos 5 min', counts?.active_accounts], ['Cadastros no período', counts?.new_accounts], ['Exclusões auditadas', counts?.deleted_accounts]] as const
  return <div className="admin-overview">
    <div className="admin-overview-heading"><div><h1>Visão geral</h1><p>Operação e audiência · somente dados agregados</p></div><label>Período<select value={days} onChange={event => setDays(Number(event.target.value))}>{[7, 30, 90].map(value => <option key={value} value={value}>{value} dias</option>)}</select></label></div>
    <div className="admin-metric-stats">{stats.map(([label, value]) => <Panel key={label} surface="dark" className="admin-metric-stat"><strong>{number(value)}</strong><span>{label}</span></Panel>)}</div>
    <div className="admin-metric-grid">
      <Panel surface="dark" className="admin-metric-card"><div className="admin-provider"><h2>Supabase</h2><span>{status[data.supabase.status]}</span></div><dl><div><dt>Banco de dados</dt><dd>{number(data.supabase.database_bytes == null ? null : data.supabase.database_bytes / 1048576, ' MiB')}</dd></div><div><dt>Conexões / limite</dt><dd>{number(data.supabase.connections)} / {number(data.supabase.max_connections)}</dd></div><div><dt>Consulta de observabilidade</dt><dd>{number(data.supabase.latency_ms, ' ms')}</dd></div></dl></Panel>
      <Panel surface="dark" className="admin-metric-card admin-render-card">
        <div className="admin-provider"><h2>Render</h2><span>{status[data.render.status]}</span></div>
        <p>Serviço monitorado · amostras de 24 horas</p>
        <div className="admin-render-resources">
          {(['cpu', 'memory', 'cpu_limit', 'memory_limit', 'bandwidth'] as const).map(key => {
            const metric = data.render[key]
            const label = { cpu: 'CPU em uso', memory: 'Memória em uso', cpu_limit: 'Limite de CPU', memory_limit: 'Limite de memória', bandwidth: 'Tráfego por intervalo' }[key]
            const factor = metric?.unit === 'bytes' ? 1048576 : 1
            const unit = metric?.unit === 'bytes' ? 'MiB' : metric?.unit === 'mb' ? 'MB' : metric?.unit
            return <div className="admin-resource" key={key}>
              <span>{label}</span><strong>{number(metric ? metric.value / factor : null, metric ? ` ${unit}` : '')}</strong>
              {metric && <>
                {!key.endsWith('_limit') && metric.values.length > 0 && <MetricTrend values={metric.values.map(value => value / factor)} timestamps={metric.timestamps} label={`${label}: ${number(metric.value / factor)} ${unit}. Últimas 24 horas.`} compact />}
                <time dateTime={metric.timestamp}>Amostra: {new Date(metric.timestamp).toLocaleString('pt-BR')}</time>
                {!key.endsWith('_limit') && metric.values.length > 0 && <details className="admin-resource-history"><summary>Consultar amostras</summary><div className="admin-metric-table"><table><thead><tr><th>Horário</th><th>{unit}</th></tr></thead><tbody>{metric.values.map((value, index) => <tr key={metric.timestamps[index]}><td>{new Date(metric.timestamps[index]).toLocaleString('pt-BR')}</td><td>{number(value / factor)}</td></tr>)}</tbody></table></div></details>}
              </>}
            </div>
          })}
        </div>
        <p>Intervalos sem amostras não representam consumo zero.</p>
      </Panel>
      <Panel surface="dark" className="admin-metric-card admin-growth"><h2>Atividade da aplicação</h2><p>Volume diário de requisições · horário de Brasília</p>{data.daily.length ? <><div className="admin-chart" ><MetricTrend values={data.daily.map(point => point.requests)} label={`Requisições diárias: ${number(counts?.requests)} no período.`} start={data.daily[0]?.date.split('-').reverse().slice(0, 2).join('/')} end={data.daily[data.daily.length - 1]?.date.split('-').reverse().slice(0, 2).join('/')} /></div><div className="admin-chart-legend"><span>● Requisições</span><span>Cadastros e exclusões na tabela</span></div><details><summary>Consultar dados do gráfico</summary><div className="admin-metric-table"><table><thead><tr><th>Data</th><th>Cadastros</th><th>Exclusões</th><th>Requisições</th></tr></thead><tbody>{data.daily.map(point => <tr key={point.date}><td>{point.date.split('-').reverse().join('/')}</td><td>{point.registrations}</td><td>{point.deletions}</td><td>{point.requests}</td></tr>)}</tbody></table></div></details></> : <p>Histórico indisponível.</p>}</Panel>
      <Panel surface="dark" className="admin-metric-card"><h2>Planos cadastrados</h2><p>Perfil principal · não confirma pagamento</p>{counts && <PlanRings values={[counts.free_accounts, counts.plus_accounts, counts.premium_accounts]} total={counts.accounts} />}{[['Free', counts?.free_accounts], ['Plus', counts?.plus_accounts], ['Premium', counts?.premium_accounts]].map(([label, value]) => <div className="admin-plan" key={label}><span>{label}</span><strong>{number(value as number | undefined)}</strong></div>)}<p>{data.unavailable.paying_accounts}</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><h2>Uso da aplicação</h2><dl><div><dt>Requisições</dt><dd>{number(counts?.requests)}</dd></div><div><dt>Respostas com erro</dt><dd>{number(counts?.errors)}</dd></div><div><dt>Latência média / p95</dt><dd>{number(counts?.avg_latency_ms, ' ms')} / {number(counts?.p95_latency_ms, ' ms')}</dd></div></dl></Panel>
      <Panel surface="dark" className="admin-metric-card"><h2>Cobertura de dados</h2><ul className="admin-coverage">{[data.unavailable.traffic_sources, data.unavailable.session_time, data.unavailable.location].map(reason => <li key={reason}>{reason}</li>)}</ul></Panel>
    </div>
    <details className="admin-metric-notes"><summary>Como interpretar os números</summary><ul>{data.notes.map(note => <li key={note}>{note}</li>)}</ul></details>
    <p className="admin-muted">Atualizado em {new Date(data.updated_at).toLocaleString('pt-BR')} · consulta a cada minuto; horário indica a coleta</p>
  </div>
}
