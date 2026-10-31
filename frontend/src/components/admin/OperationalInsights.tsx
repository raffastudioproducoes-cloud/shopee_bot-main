import { useQuery } from '@tanstack/react-query'
import { adminMetricsApi } from '../../api/adminMetrics'
import { CardTags } from './CardTags'
import { Panel } from '../ui/Panel'

const fmt = (n: number | null | undefined) => n == null ? 'Indisponível' : n.toLocaleString('pt-BR', {maximumFractionDigits: 1})
const money = (n: number | null | undefined) => n == null ? 'Indisponível' : n.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})

export function OperationalInsights({ accountCount }: { accountCount?: number | null }) {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'operations'],
    queryFn: adminMetricsApi.getOperations,
    refetchInterval: 60_000,
    retry: 1,
  })
  const db = data?.status === 'available' ? data.database : null
  const q = data?.status === 'available' ? data.queries : null
  const up = data?.status === 'available' ? data.uptime : null
  return <section className="admin-scale-section" aria-label="Observabilidade avançada">
    <div className="admin-section-heading"><span>OPERAÇÃO AVANÇADA</span><h2>Desempenho, disponibilidade e custos</h2><p>Observações agregadas e estimativas; dados ausentes não representam zero.</p></div>
    <div className="admin-scale-grid">
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['supabase', 'database', 'performance']}/><h3>Desempenho PostgreSQL</h3>
        {db && q ? <>
          <dl><div><dt>Conexões ativas</dt><dd>{fmt(db.active)}</dd></div>
            <div><dt>Conexões ociosas</dt><dd>{fmt(db.idle)}</dd></div>
            <div><dt>Ociosas em transação</dt><dd>{fmt(db.idle_in_transaction)}</dd></div>
            <div><dt>Bloqueadas</dt><dd>{fmt(db.blocked)}</dd></div>
            <div><dt>Limite PostgreSQL</dt><dd>{fmt(db.max_connections)}</dd></div>
            <div><dt>Padrões registrados</dt><dd>{fmt(q.tracked_statements)}</dd></div>
            <div><dt>Padrões com média acima de 50 ms (mín. 5 chamadas)</dt><dd>{fmt(q.slow_patterns)}</dd></div></dl>
          {q.worst.length > 0 && <details><summary>5 padrões mais custosos (sem revelar SQL)</summary>
            <div className="admin-metric-table"><table><thead><tr><th>Posição</th><th>Chamadas</th><th>Média · ms</th><th>Pico · ms</th></tr></thead>
              <tbody>{q.worst.map(item => <tr key={item.rank}><td>#{item.rank}</td><td>{fmt(item.calls)}</td><td>{fmt(item.mean_ms)}</td><td>{fmt(item.max_ms)}</td></tr>)}</tbody>
            </table></div></details>}
          <p>Amostra das sessões visíveis. Limite do PostgreSQL não equivale à ocupação do pool Supavisor; estatísticas são acumuladas e não representam apenas o período selecionado.</p>
        </> : <p role="status">{isLoading ? 'Consultando...' : 'Estatísticas indisponíveis nesta coleta.'}</p>}
      </Panel>
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['app', 'history', 'diagnosis']}/><h3>Disponibilidade amostrada</h3>
        {up?.status === 'sampled' ? <>
          <dl><div><dt>Verificações OK</dt><dd>{fmt(up.ok)}</dd></div><div><dt>Respostas com erro</dt><dd>{fmt(up.error)}</dd></div><div><dt>Sem resposta conclusiva</dt><dd>{fmt(up.unanswered)}</dd></div>
            <div><dt>Resultado mais recente</dt><dd>{up.latest === 'ok' ? 'OK' : up.latest === 'error' ? 'Erro' : 'Não conclusivo'}</dd></div>
            <div><dt>Taxa de respostas OK (exclui inconclusivos)</dt><dd>{up.ok + up.error > 0 ? fmt(100 * up.ok / (up.ok + up.error)) + '%' : 'Indisponível'}</dd></div></dl>
          <details><summary>Últimas verificações</summary><div className="admin-metric-table"><table><thead><tr><th>Instante</th><th>Resultado</th></tr></thead><tbody>
            {up.recent.map(x => <tr key={x.at}><td>{new Date(x.at).toLocaleString('pt-BR', {timeZone:'America/Sao_Paulo'})}</td><td>{x.status === 'ok' ? 'OK' : x.status === 'error' ? 'Erro' : 'Inconclusivo'}</td></tr>)}
          </tbody></table></div></details>
          <p>Verificações a cada 5 minutos de /health/ready; sondas sem resposta são inconclusivas. Não equivale a SLA, uptime contínuo ou monitoramento externo independente.</p>
        </> : <p role="status">{isLoading ? 'Consultando...' : 'Aguardando verificações automáticas válidas.'}</p>}
      </Panel>
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['clients', 'coverage']} /><h3>Origem declarada dos clientes</h3>
        <p>Somente respostas voluntárias em grupos de três ou mais participantes.</p>
        {data?.acquisition.status === 'available' ? <>
          <p>{fmt(data.acquisition.declared_total)} respostas registradas.</p>
          {data.acquisition.groups.length ? <dl>{data.acquisition.groups.map(row => <div key={row.source}>
            <dt>{{search:'Buscas', social:'Redes sociais', referral:'Indicações', direct:'Acesso direto', other:'Outros'}[row.source as 'search'|'social'|'referral'|'direct'|'other'] ?? 'Outro'}</dt><dd>{fmt(row.accounts)}</dd>
          </div>)}</dl> : <p>Nenhuma categoria atingiu o mínimo de três respostas; não são exibidas informações individuais.</p>}
          <p>Não é atribuição de conversão ou análise automática de UTMs. Respostas podem ser modificadas ou excluídas pelo titular.</p>
        </> : <p>Coleta declarada indisponível.</p>}
      </Panel>
      <Panel surface="dark" className="admin-metric-card">
        <CardTags tags={['app', 'plans', 'consumption']}/><h3>Custos operacionais estimados</h3>
        {data?.costs.status === 'estimate' ? <dl><div><dt>Orçamento mensal informado</dt><dd>{money(data.costs.monthly_brl)}</dd></div><div><dt>Equivalente diário (30 dias)</dt><dd>{money(data.costs.daily_brl)}</dd></div><div><dt>Rateio mensal por conta cadastrada</dt><dd>{accountCount && data.costs.monthly_brl != null ? money(data.costs.monthly_brl / accountCount) : 'Indisponível'}</dd></div></dl>
          : <p>Orçamento não configurado. Defina ADMIN_ESTIMATED_MONTHLY_BRL no backend do Render para informar o custo mensal em reais.</p>}
        <p>Valor ilustrativo definido pelo operador, não extraído do Render ou Supabase. Não se trata de fatura ou cobrança confirmada. O rateio por conta divide um orçamento informado entre contas existentes e não mede custo efetivo individual. Atribuição por conta exige medições e faturas reais.</p>
      </Panel>
    </div>
  </section>
}
