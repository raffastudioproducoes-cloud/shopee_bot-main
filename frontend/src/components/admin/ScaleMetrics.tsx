import { useQuery } from '@tanstack/react-query'
import { adminMetricsApi, type AdminMetrics } from '../../api/adminMetrics'
import { Panel } from '../ui/Panel'
import { MetricTrend } from './MetricTrend'
import { CardTags } from './CardTags'
import { capacityPercent, formatMetricTime, isStale } from './metricsPresentation'

const value = (n: number | null | undefined, unit = '') => n == null ? 'Indisponível' : `${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${unit}`

function Gauge({ label, percent, timestamp }: { label: string; percent: number | null; timestamp?: string }) {
  return <div className="admin-capacity-gauge"><svg viewBox="0 0 120 120" role="img" aria-label={`${label}: ${value(percent, '%')}`}>
    <circle cx="60" cy="60" r="46" className="admin-gauge-track" />
    {percent != null && <circle cx="60" cy="60" r="46" className="admin-gauge-value" pathLength="100" strokeDasharray={`${Math.min(100, percent)} 100`} transform="rotate(-90 60 60)" />}
    <text x="60" y="64" textAnchor="middle">{percent == null ? '—' : value(percent, '%')}</text>
  </svg><strong>{label}</strong>{timestamp && <small>Amostra: {formatMetricTime(timestamp)}{isStale(timestamp, 7_200_000) ? ' · Antiga' : ''}</small>}</div>
}

export function ScaleMetrics({ data }: { data: AdminMetrics }) {
  const { data: queue, isLoading: queueLoading, error: queueError } = useQuery({
    queryKey: ['admin', 'queue-health'],
    queryFn: adminMetricsApi.getQueueHealth,
    refetchInterval: 60_000,
    retry: 1,
  })
  const queueCounts = queue?.status === 'available' ? queue.counts : null
  const metrics = data.scale
  const db = metrics?.database
  const operations = metrics?.operations
  const engagement = metrics?.engagement
  const history = metrics?.capacity_history ?? []
  const firstCapacityDay = history[0]
  const lastCapacityDay = history[history.length - 1]
  const capacityDeltaMiB = firstCapacityDay && lastCapacityDay
    ? (lastCapacityDay.database_bytes - firstCapacityDay.database_bytes) / 1048576
    : null
  const cpu = capacityPercent(data.render.cpu, data.render.cpu_limit)
  const memory = capacityPercent(data.render.memory, data.render.memory_limit)
  const notices: string[] = []
  if (db?.blocked_connections) notices.push(`${db.blocked_connections} conexões bloqueadas nesta consulta. Investigue transações antes de aumentar o servidor.`)
  if ((db?.oldest_transaction_seconds ?? 0) > 60) notices.push('Há transação aberta há mais de um minuto. Verifique se está prendendo recursos.')
  if (metrics?.rate_limited_requests) notices.push('A aplicação respondeu 429. Investigue limites internos; isso não confirma bloqueio de uma rede social.')
  if (data.render.cpu && !isStale(data.render.cpu.timestamp, 7_200_000) && cpu != null && cpu >= 80) notices.push('CPU acima de 80% na última amostra. Confirme duração e fila antes de escalar.')
  if (data.render.memory && !isStale(data.render.memory.timestamp, 7_200_000) && memory != null && memory >= 80) notices.push('Memória acima de 80% na última amostra. Investigue crescimento e picos antes de escalar.')
  return <section className="admin-scale-section" aria-labelledby="admin-scale-title">
    <div className="admin-section-heading"><span>CONTROLE DA OPERAÇÃO</span><h2 id="admin-scale-title">Capacidade e crescimento</h2><p>Sinais para investigar gargalos e planejar a expansão.</p>{metrics?.collected_at && <p>Banco e clientes: coleta de {formatMetricTime(metrics.collected_at)} · Brasília{isStale(metrics.collected_at) ? ' · Dados antigos' : ''}</p>}</div>
    <div className="admin-scale-grid">
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['render', 'capacity']} /><h3>Capacidade do Render</h3><div className="admin-capacity-pair"><Gauge label="CPU / limite" percent={cpu} timestamp={data.render.cpu?.timestamp} /><Gauge label="RAM / limite" percent={memory} timestamp={data.render.memory?.timestamp} /></div><p>Percentuais de amostras compatíveis. Pico sustentado e disponibilidade exigem histórico próprio e sondas externas.</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'logs', 'performance']} /><h3>Saúde da aplicação</h3><dl><div><dt>Latência p99</dt><dd>{value(metrics?.p99_latency_ms, ' ms')}</dd></div><div><dt>Erros de servidor · 5xx</dt><dd>{value(metrics?.server_errors)}</dd></div><div><dt>Respostas 429 · aplicação</dt><dd>{value(metrics?.rate_limited_requests)}</dd></div><div><dt>Respostas com erro / total</dt><dd>{value(data.counts?.requests ? data.counts.errors / data.counts.requests * 100 : null, '%')}</dd></div></dl><p>Logs disponíveis no período. Não equivale a disponibilidade nem a erros dos provedores.</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'database', 'capacity']} /><h3>Banco · pressão e espaço</h3><dl><div><dt>Conexões bloqueadas agora</dt><dd>{value(db?.blocked_connections)}</dd></div><div><dt>Transação aberta mais antiga</dt><dd>{value(db?.oldest_transaction_seconds, ' s')}</dd></div></dl>{db?.tables.length ? <details><summary>Tamanho por tabela e índices</summary><div className="admin-metric-table"><table><thead><tr><th>Tabela</th><th>Dados · MiB</th><th>Índices · MiB</th></tr></thead><tbody>{db.tables.map(table => <tr key={table.name}><td>{table.name}</td><td>{value(table.table_bytes / 1048576)}</td><td>{value(table.index_bytes / 1048576)}</td></tr>)}</tbody></table></div></details> : <p>Tamanho por tabela indisponível nesta coleta.</p>}<p>Snapshot das sessões visíveis ao coletor. Histórico diário de crescimento ativo; ocupação do pool, cota de disco e consultas mais caras ainda sem coleta.</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'scheduler', 'publishing']} /><h3>Publicações e agendamentos</h3><dl><div><dt>Agendamentos cadastrados</dt><dd>{value(operations?.scheduled)}</dd></div><div><dt>Eventos de sucesso / falha</dt><dd>{value(operations?.published_events)} / {value(operations?.failed_events)}</dd></div><div><dt>Contas que publicaram no período</dt><dd>{value(operations?.publishing_accounts)}</dd></div></dl><p>Eventos preservados, não posts únicos. Agendamentos incluem recorrências e não representam fila pendente. Duração, tentativas e idade da fila ainda sem instrumentação.</p></Panel>
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['supabase', 'scheduler', 'diagnosis']} />
        <h3>Saúde da fila de publicações</h3>
        {queueCounts ? <>
          <dl>
            <div><dt>Aguardando execução</dt><dd>{value(queueCounts.pending)}</dd></div>
            <div><dt>Em execução</dt><dd>{value(queueCounts.running)}</dd></div>
            <div><dt>Concluídas</dt><dd>{value(queueCounts.succeeded)}</dd></div>
            <div><dt>Confirmadas manualmente</dt><dd>{value(queueCounts.manually_confirmed)}</dd></div>
            <div><dt>Falhas registradas</dt><dd>{value(queueCounts.failed)}</dd></div>
            <div><dt>Sem confirmação</dt><dd>{value(queueCounts.unknown)}</dd></div>
            <div><dt>Execuções com mais de uma tentativa</dt><dd>{value(queueCounts.multiple_attempts)}</dd></div>
          </dl>
          {queueCounts.unknown > 0 && <p role="status" className="admin-data-notice">
            Atenção: {queueCounts.unknown} {queueCounts.unknown === 1 ? 'publicação precisa' : 'publicações precisam'} de conferência
            {queue?.oldest_unknown_minutes != null ? ` (mais antiga há ${value(queue.oldest_unknown_minutes)} min)` : ''}.
            Não reenvie sem verificar o resultado na rede.
          </p>}
          {queueCounts.running > 0 && queue?.oldest_running_minutes != null &&
            <p>Execução ativa mais antiga: {value(queue.oldest_running_minutes)} min.</p>}
          <p>Total registrado desde o início da fila: {value(queueCounts.total)} execuções, não posts únicos.
            Os contadores não são limitados pelo filtro de período acima. Estados sem confirmação não significam falha.</p>
          <p><a href="/posts">Ver postagens e conciliar resultados incertos</a></p>
        </> : <p role="status">
          {queueLoading ? 'Consultando a fila...' :
            queueError || queue?.status === 'unavailable'
              ? 'Não foi possível consultar a fila. O estado é desconhecido; não significa zero execuções.'
              : 'Dados da fila ainda não disponíveis.'}
        </p>}
      </Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'clients', 'retention']} /><h3>Clientes · retorno semanal</h3><dl><div><dt>Ativos nos últimos 7 dias</dt><dd>{value(engagement?.active_week)}</dd></div><div><dt>Ativos nos 7 dias anteriores</dt><dd>{value(engagement?.previous_week)}</dd></div><div><dt>Presentes em ambas as semanas</dt><dd>{value(engagement?.returning_week)}</dd></div><div><dt>Retorno sobre semana anterior</dt><dd>{value(engagement?.previous_week ? engagement.returning_week / engagement.previous_week * 100 : null, '%')}</dd></div></dl><p>Requisições autenticadas bem-sucedidas de contas existentes. Janela fixa de 14 dias; não mede tempo ativo nem retenção por coorte de cadastro.</p></Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['supabase', 'plans', 'consumption']} /><h3>Consumo por plano</h3>{metrics?.consumption?.length ? <div className="admin-metric-table"><table><thead><tr><th>Plano atual</th><th>Requisições</th><th>Duração acumulada · s</th></tr></thead><tbody>{metrics.consumption.map(row => <tr key={row.plan}><td>{row.plan === 'unknown' ? 'Sem plano' : row.plan}</td><td>{value(row.requests)}</td><td>{value(row.request_duration_ms / 1000)}</td></tr>)}</tbody></table></div> : <p>Consumo por plano indisponível nesta coleta.</p>}<p>Contas existentes com requisições identificadas; usa o plano atual. Duração inclui espera e não representa CPU nem custo. Custo por cliente e publicação exige faturamento e atribuição de consumo.</p></Panel>
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['supabase', 'database', 'history']} />
        <h3>Evolução do banco</h3>
        {lastCapacityDay ? <>
          <p role="status">
            {history.length} {history.length === 1 ? 'dia observado' : 'dias observados'} ·
            Última medição: {lastCapacityDay.date.split('-').reverse().join('/')} ·
            Banco: {value(lastCapacityDay.database_bytes / 1048576, ' MiB')} ·
            Conexões observadas: {value(lastCapacityDay.observed_connections)}.
          </p>
          {history.length === 1 ? (
            <p>Primeira amostra registrada. O gráfico de evolução aparecerá quando houver medições de pelo menos dois dias distintos. Não existe tendência calculada ainda.</p>
          ) : <>
            <MetricTrend
              values={history.map(point => point.database_bytes / 1048576)}
              timestamps={history.map(point => `${point.date}T12:00:00-03:00`)}
              label={`Tamanho do banco em MiB nos ${history.length} dias observados`}
              start={firstCapacityDay?.date.split('-').reverse().slice(0, 2).join('/')}
              end={lastCapacityDay.date.split('-').reverse().slice(0, 2).join('/')}
            />
            <p>Variação entre a primeira e a última medição: {capacityDeltaMiB != null && capacityDeltaMiB > 0 ? '+' : ''}{value(capacityDeltaMiB, ' MiB')}.</p>
          </>}
          <details>
            <summary>Consultar {history.length === 1 ? 'a medição registrada' : 'os dias registrados'}</summary>
            <div className="admin-metric-table"><table>
              <thead><tr><th>Dia</th><th>Banco · MiB</th><th>Conexões observadas</th></tr></thead>
              <tbody>{history.map(point => (
                <tr key={point.date}>
                  <td>{point.date.split('-').reverse().join('/')}</td>
                  <td>{value(point.database_bytes / 1048576)}</td>
                  <td>{value(point.observed_connections)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          </details>
          <p>Captura automática programada diariamente às 00h15 (Brasília). Cada dia apresenta a última medição do tamanho do banco e o maior número de conexões entre as coletas daquele dia.</p>
        </> : (
          <p role="status">{data.supabase.status === 'available'
            ? 'Ainda não há medições históricas. A rotina automática está programada para 00h15 (Brasília).'
            : 'Histórico indisponível porque não foi possível consultar as métricas do banco.'}</p>
        )}
        <p>Lacunas não são zeros; medições pontuais não mostram picos contínuos nem a cota de armazenamento contratada. Previsões de esgotamento exigem histórico representativo.</p>
      </Panel>
      <Panel surface="dark" className="admin-metric-card"><CardTags tags={['app', 'coverage']} /><h3>Cobertura para expansão</h3><details><summary>Fontes necessárias para completar o controle</summary><ul className="admin-coverage"><li>Estatísticas de consultas agregadas, ocupação do pool e limites reais do plano.</li><li>Sondas de disponibilidade e histórico de saturação do servidor.</li><li>Eventos de tarefa: início, conclusão, tentativas e código de erro do provedor.</li><li>Eventos de ativação e cobrança confirmada para funil, conversão e cancelamentos.</li><li>Fatura e consumo agregado para custo por conta ativa e publicação concluída.</li></ul></details></Panel>
    </div>
    <Panel surface="dark" className="admin-metric-card admin-scale-notices"><CardTags tags={['app', 'diagnosis']} /><h3>Diagnóstico para decisão</h3>{notices.length ? <ul>{notices.map(notice => <li key={notice}>{notice}</li>)}</ul> : <p>Nenhum aviso pelos sinais disponíveis. Cobertura incompleta não confirma que toda a operação esteja saudável.</p>}<p>Os avisos sugerem investigação. Nenhuma ação de escala é executada.</p></Panel>
  </section>
}
