import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminMetricsApi } from '../api/adminMetrics'
import { Panel } from '../components/ui/Panel'
import { MetricTrend, PlanRings } from '../components/admin/MetricTrend'
import { ScaleMetrics } from '../components/admin/ScaleMetrics'
import { OperationalInsights } from '../components/admin/OperationalInsights'
import { CardTags } from '../components/admin/CardTags'
import { LocationGlobe } from '../components/admin/LocationGlobe'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'
import { ApiError } from '../lib/api'
import { comparisonDelta, formatMetricTime, isStale } from '../components/admin/metricsPresentation'

const number = (value: number | null | undefined, suffix = '') => value == null ? 'Indisponível' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}${suffix}`
const status = { available: 'Conectado', partial: 'Dados parciais', unavailable: 'Indisponível', not_configured: 'Não configurado' }
const diagnosticLabels: Record<string, string> = {
  timeout: 'A consulta excedeu o tempo disponível. Tente atualizar.',
  permission_denied: 'A API não tem acesso à função de métricas. Verifique a credencial service_role no servidor.',
  rpc_missing: 'A função admin_metrics_snapshot está ausente ou não foi encontrada pela API.',
  invalid_response: 'O provedor enviou informações incompatíveis com o contrato esperado.',
  provider_error: 'A leitura falhou. Consulte os logs do servidor, sem expor credenciais.',
  api_rejected: 'O Render recusou a credencial ou a permissão de consulta de métricas.',
  bad_request: 'O Render retornou HTTP 400 mesmo na consulta mínima. Verifique os parâmetros aceitos pela API.',
  no_samples: 'O Render não retornou amostras para alguns dos indicadores na última hora.',
  not_configured: 'Configure RENDER_METRICS_API_KEY somente no serviço backend do Render.',
}


export default function AdminOverviewPage() {
  const [days, setDays] = useState(30)
  const [compare, setCompare] = useState(false)
  const { data, isLoading, isFetching, error, refetch } = useQuery({ queryKey: ['admin', 'metrics', days], queryFn: () => adminMetricsApi.get(days), refetchInterval: 60_000, retry: 1 })
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return <p role="alert">Acesso às métricas não autorizado. Reentre com uma conta administrativa.</p>
  if (isLoading) return <PageSkeleton variant="cards" heading={false} count={2} />
  if (!data) return <div><p role="alert">Não foi possível carregar as métricas administrativas.</p><Button onClick={() => { void refetch() }}>Tentar novamente</Button></div>
  const counts = data.counts
  const stats = [
    ['Contas atuais', counts?.accounts, ['supabase', 'clients']],
    ['Ativos · últimos 5 min', counts?.active_accounts, ['supabase', 'clients']],
    ['Cadastros no período', counts?.new_accounts, ['supabase', 'clients']],
    ['Exclusões auditadas', counts?.deleted_accounts, ['supabase', 'clients']],
  ] as const
  return <div className="admin-overview">
    <div className="admin-overview-heading"><div><h1>Visão geral</h1><p>Operação e audiência · somente dados agregados</p></div><label>Período<select value={days} onChange={event => setDays(Number(event.target.value))}>{[7, 30, 90].map(value => <option key={value} value={value}>{value} dias</option>)}</select></label></div>
    <div className="admin-collection-state" aria-live="polite">
      <p>Última coleta: {formatMetricTime(data.updated_at)} · Brasília{isStale(data.updated_at) ? ' · Dados antigos' : ''}{isFetching ? ' · Atualizando…' : ''}</p>
      <Button variant="secondary" disabled={isFetching} onClick={() => { void refetch() }}>Atualizar agora</Button>
      <Button variant="ghost" aria-pressed={compare} onClick={() => setCompare(!compare)}>Comparar com período anterior</Button>
    </div>
    {error && <p className="admin-data-notice" role="alert">A atualização falhou. Os últimos dados disponíveis foram preservados; confira o horário da coleta.</p>}
    {(data.supabase.diagnostic || data.render.diagnostic) && <section className="admin-data-notice" aria-label="Diagnóstico das fontes" role="status">
      <strong>Diagnóstico da coleta</strong>
      {data.supabase.diagnostic && <p>Supabase: {diagnosticLabels[data.supabase.diagnostic] ?? 'Falha na coleta.'}</p>}
      {data.render.diagnostic && <p>Render: {diagnosticLabels[data.render.diagnostic] ?? 'Falha na coleta.'}</p>}
      {data.render.missing_metrics && data.render.missing_metrics.length > 0 &&
        <p>Sem amostras disponíveis para: {data.render.missing_metrics.join(', ')}.</p>}
    </section>}
    {data.status !== 'available' && <p className="admin-data-notice" role="status">{data.status === 'unavailable' ? 'Provedores indisponíveis. Nenhum valor foi estimado.' : 'Cobertura parcial. Alguns indicadores ainda não estão disponíveis.'}</p>}
    <div className="admin-metric-stats">{stats.map(([label, value, tags]) => <Panel key={label} surface="dark" className="admin-metric-stat"><CardTags tags={tags} /><strong>{number(value)}</strong><span>{label}</span></Panel>)}</div>
    {compare && (data.previous_period && counts ? <section aria-label="Comparação entre períodos" className="admin-period-comparison">
      <p>Atual inclui hoje incompleto. Anterior: {data.previous_period.starts_on.split('-').reverse().join('/')} a {data.previous_period.ends_on.split('-').reverse().join('/')} — dias completos.</p>
      <div className="admin-metric-stats">{[
        ['Cadastros existentes', counts.new_accounts, data.previous_period.registrations],
        ['Exclusões auditadas', counts.deleted_accounts, data.previous_period.deletions],
        ['Requisições', counts.requests, data.previous_period.requests],
        ['Respostas com erro', counts.errors, data.previous_period.errors],
      ].map(([label, current, previous]) => <Panel key={label} surface="dark" className="admin-comparison-card"><CardTags tags={['supabase', 'comparison']} /><h2>{label}</h2><strong>{number(current as number)}</strong><p>Anterior: {number(previous as number)}</p><span>{comparisonDelta(current as number, previous as number)}</span></Panel>)}</div>
    </section> : <p role="status">Comparação indisponível nesta coleta.</p>)}
    <LocationGlobe data={data} />
    <div className="admin-metric-grid">
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'database']} /><div className="admin-provider"><h2>Supabase</h2><span>{status[data.supabase.status]}</span></div><dl><div><dt>Banco de dados</dt><dd>{number(data.supabase.database_bytes == null ? null : data.supabase.database_bytes / 1048576, ' MiB')}</dd></div><div><dt>Conexões / limite</dt><dd>{number(data.supabase.connections)} / {number(data.supabase.max_connections)}</dd></div><div><dt>Consulta de observabilidade</dt><dd>{number(data.supabase.latency_ms, ' ms')}</dd></div></dl></Panel>
      <Panel surface="dark" className="admin-metric-card admin-render-card">
        <CardTags tags={['render', 'capacity']} />
        <div className="admin-provider"><h2>Render</h2><span>{status[data.render.status]}</span></div>
        <p>Serviço monitorado · amostras da última hora</p>
        <div className="admin-render-resources">
          {(['cpu', 'memory', 'cpu_limit', 'memory_limit', 'bandwidth'] as const).map(key => {
            const metric = data.render[key]
            const label = { cpu: 'CPU em uso', memory: 'Memória em uso', cpu_limit: 'Limite de CPU', memory_limit: 'Limite de memória', bandwidth: 'Tráfego por intervalo' }[key]
            const factor = metric?.unit === 'bytes' ? 1048576 : 1
            const unit = metric?.unit === 'bytes' ? 'MiB' : metric?.unit === 'mb' ? 'MB' : metric?.unit
            return <div className="admin-resource" key={key}>
              <span>{label}</span><strong>{number(metric ? metric.value / factor : null, metric ? ` ${unit}` : '')}</strong>
              {metric && <>
                {!key.endsWith('_limit') && metric.values.length > 0 && <MetricTrend values={metric.values.map(value => value / factor)} timestamps={metric.timestamps} label={`${label}: ${number(metric.value / factor)} ${unit}. Última hora.`} compact />}
                <time dateTime={metric.timestamp}>Amostra: {formatMetricTime(metric.timestamp)} · Brasília{isStale(metric.timestamp, 7_200_000) ? ' · Amostra antiga' : ''}</time>
                {!key.endsWith('_limit') && metric.values.length > 0 && <details className="admin-resource-history"><summary>Consultar amostras</summary><div className="admin-metric-table"><table><thead><tr><th>Horário de Brasília</th><th>{unit}</th></tr></thead><tbody>{metric.values.map((value, index) => <tr key={metric.timestamps[index]}><td>{formatMetricTime(metric.timestamps[index])}</td><td>{number(value / factor)}</td></tr>)}</tbody></table></div></details>}
              </>}
            </div>
          })}
        </div>
        <p>Intervalos sem amostras não representam consumo zero.</p>
      </Panel>
      <Panel surface="dark" className="admin-metric-card admin-growth"><CardTags tags={['supabase', 'traffic']} /><h2>Atividade da aplicação</h2><p>Volume diário de requisições · horário de Brasília</p>{data.daily.length ? <><div className="admin-chart" ><MetricTrend values={data.daily.map(point => point.requests)} label={`Requisições diárias: ${number(counts?.requests)} no período.`} start={data.daily[0]?.date.split('-').reverse().slice(0, 2).join('/')} end={data.daily[data.daily.length - 1]?.date.split('-').reverse().slice(0, 2).join('/')} /></div><div className="admin-chart-legend"><span>● Requisições</span><span>Cadastros e exclusões na tabela</span></div><details><summary>Consultar dados do gráfico</summary><div className="admin-metric-table"><table><thead><tr><th>Data</th><th>Cadastros</th><th>Exclusões</th><th>Requisições</th></tr></thead><tbody>{data.daily.map(point => <tr key={point.date}><td>{point.date.split('-').reverse().join('/')}</td><td>{point.registrations}</td><td>{point.deletions}</td><td>{point.requests}</td></tr>)}</tbody></table></div></details></> : <p>Histórico indisponível.</p>}</Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'clients', 'plans']} /><h2>Planos cadastrados</h2><p>Perfil principal · não confirma pagamento</p>{counts && <PlanRings values={[counts.free_accounts, counts.plus_accounts, counts.premium_accounts]} total={counts.accounts} />}{[['Free', counts?.free_accounts], ['Plus', counts?.plus_accounts], ['Premium', counts?.premium_accounts]].map(([label, value]) => <div className="admin-plan" key={label}><span>{label}</span><strong>{number(value as number | undefined)}</strong></div>)}<p>{data.unavailable.paying_accounts}</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'performance']} /><h2>Uso da aplicação</h2><dl><div><dt>Requisições</dt><dd>{number(counts?.requests)}</dd></div><div><dt>Respostas com erro</dt><dd>{number(counts?.errors)}</dd></div><div><dt>Latência média / p95</dt><dd>{number(counts?.avg_latency_ms, ' ms')} / {number(counts?.p95_latency_ms, ' ms')}</dd></div></dl></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['app', 'coverage']} /><h2>Cobertura de dados</h2><p>Regiões: não coletadas. O mapa só poderá mostrar agregados reais após consentimento e uma fonte de localização adequada.</p>{data.scale && <p>Histórico de capacidade: {data.scale.capacity_history?.length
        ? `${data.scale.capacity_history.length} ${data.scale.capacity_history.length === 1 ? 'dia observado' : 'dias observados'}; veja a evolução abaixo. Coleta automática programada para 00h15 (Brasília).`
        : data.supabase.status === 'available'
          ? 'Ainda sem histórico. Coleta diária programada às 00h15 (Brasília); ausência de medições não representa consumo zero.'
          : 'Indisponível porque a consulta do banco falhou.'}</p>}<ul className="admin-coverage">{[data.unavailable.traffic_sources, data.unavailable.session_time, data.unavailable.location].map(reason => <li key={reason}>{reason}</li>)}</ul></Panel>
    </div>
    <ScaleMetrics data={data} />
    <OperationalInsights />
    <details className="admin-metric-notes"><summary>Como interpretar os números</summary><ul>{data.notes.map(note => <li key={note}>{note}</li>)}</ul></details>
    <p className="admin-muted">Consulta automática a cada minuto. Uma nova consulta pode retornar amostras antigas; confira os horários acima.</p>
  </div>
}
