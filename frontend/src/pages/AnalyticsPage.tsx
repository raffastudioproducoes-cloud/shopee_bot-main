import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { useProfileStore } from '../stores/profileStore'
import { Select } from '../components/ui/Select'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'

type Network = 'threads' | 'facebook' | 'instagram' | 'tiktok' | 'x'
type Row = {
  network: Network
  succeeded: number
  failed: number
  unknown: number
  views: number | null
  likes: number | null
  comments: number | null
  reposts: number | null
  clicks: number | null
  insights_status: string
}
type Summary = {
  days: number
  networks: Row[]
  last_attempt_at?: string | null
  last_completed_at?: string | null
  provider_states?: Record<string, string>
  auto_refresh_hours?: number
}
type RefreshResult = { state: string; provider_states?: Record<string, string> }
type FacebookDailyValue = { period_end: string; value: number }
type ProbeResult = {
  network: string
  state: string
  metric?: string
  result_count?: number
  http_status?: number
  error_code?: number
  error_subcode?: number
  days_requested?: number
  days_returned?: number
  total_views?: number | null
  daily_values?: FacebookDailyValue[]
}
type ScopedProbe = ProbeResult & { scopeKey: string }

const names: Record<Network, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}

export default function AnalyticsPage() {
  const [days, setDays] = useState('30')
  const [network, setNetwork] = useState('all')
  const [probe, setProbe] = useState<ScopedProbe | null>(null)
  const [probing, setProbing] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState<{ scope: string; message: string } | null>(null)
  const queryClient = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
  const isAdmin = useAuthStore((state) => state.user?.access === 'ADMIN')
  const profileId = useProfileStore((state) => state.activeProfileId)
  // Do not display another account's or another period's previous result.
  const profileScope = `${userId ?? ''}:${profileId ?? ''}`
  const scopeKey = `${profileScope}:${days}`
  const visibleProbe = isAdmin && probe?.scopeKey === scopeKey ? probe : null
  const facebookViews = visibleProbe?.network === 'facebook' && visibleProbe.state === 'ok'
    ? visibleProbe.total_views ?? null : null
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', userId, profileId, days, network],
    queryFn: () => api.get<Summary>(`/analytics/summary?days=${days}${network === 'all' ? '' : `&network=${network}`}`),
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const rows = data?.networks ?? []
  const total = rows.reduce((sum, row) => sum + row.succeeded, 0)
  const failures = rows.reduce((sum, row) => sum + row.failed, 0)
  const uncertain = rows.reduce((sum, row) => sum + row.unknown, 0)

  async function refreshAll() {
    if (!profileId || refreshing) return
    setRefreshing(true)
    setRefreshMessage(null)
    try {
      const result = await api.post<RefreshResult>('/analytics/refresh', {})
      await queryClient.invalidateQueries({ queryKey: ['analytics-summary', userId, profileId] })
      setRefreshMessage({
        scope: profileScope,
        message: result.state === 'updated'
          ? 'Consulta concluída. Dados que a API não disponibilizou continuam com traço.'
          : result.state === 'recent'
            ? 'A atualização já está em andamento ou foi solicitada há menos de 5 minutos.'
            : 'Não foi possível iniciar a atualização agora.',
      })
    } catch {
      setRefreshMessage({ scope: profileScope, message: 'Falha ao atualizar. Tente novamente em alguns minutos.' })
    } finally {
      setRefreshing(false)
    }
  }

  async function testInsights(name: 'threads' | 'facebook' | 'instagram') {
    setProbing(name)
    setProbe(null)
    try {
      const result = await api.post<ProbeResult>(
        `/analytics/probe/${name}${name === 'facebook' ? `?days=${days}` : ''}`, {}
      )
      setProbe({ ...result, scopeKey })
    } catch {
      setProbe({ network: name, state: 'request_failed', scopeKey })
    } finally {
      setProbing(null)
    }
  }

  return (
    <div className="csp-s-0168">
      <header>
        <h1 className="csp-s-0169">Análise de redes</h1>
        <p className="csp-s-0170">Resultados das publicações do perfil ativo</p>
      </header>

      <div className="analytics-filters" style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <Select label="Período" value={days} onChange={(event) => setDays(event.target.value)} width={160} options={[
          { value: '7', label: '7 dias' }, { value: '30', label: '30 dias' }, { value: '90', label: '90 dias' },
        ]} />
        <Select label="Rede" value={network} onChange={(event) => setNetwork(event.target.value)} width={190} options={[
          { value: 'all', label: 'Todas' }, ...Object.entries(names).map(([value, label]) => ({ value, label })),
        ]} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, justifyContent: 'flex-end' }}>
          <Button variant="secondary" size="sm" loading={refreshing} disabled={refreshing || !profileId} onClick={refreshAll}>
            Atualizar informações
          </Button>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Automático a cada 24 horas</span>
        </div>
      </div>

      {refreshMessage?.scope === profileScope && <p role="status" style={{ color: 'var(--text-muted)', margin: '12px 0 0' }}>
        {refreshMessage.message}
      </p>}
      {data?.last_completed_at && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
        Última consulta às redes: {new Date(data.last_completed_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' })} (Brasília).
      </p>}

      {isLoading ? <PageSkeleton variant="table" heading={false} /> : error ? (
        <p role="alert" className="csp-s-0171">Não foi possível carregar as análises.</p>
      ) : (
        <>
          <div className="analytics-summary" style={{ display: 'flex', flexWrap: 'wrap', gap: 24, padding: '16px 0', borderTop: '1px solid var(--border-card)', borderBottom: '1px solid var(--border-card)' }}>
            <span><strong>{total}</strong> envios concluídos</span>
            <span><strong>{failures}</strong> falhas</span>
            <span><strong>{uncertain}</strong> sem confirmação</span>
          </div>
          <div className="analytics-desktop-table" style={{ overflowX: 'auto' }}>
            <table className="csp-s-0172">
              <thead><tr>{['Rede', 'Envios concluídos', 'Falhas', 'Sem confirmação', 'Visualizações', 'Curtidas', 'Comentários', 'Reposts', 'Cliques'].map((label) => (
                <th key={label} scope="col" className="csp-s-0173">{label}</th>
              ))}</tr></thead>
              <tbody>{rows.map((row) => (
                <tr key={row.network}>
                  <th scope="row" className="csp-s-0174">{names[row.network]}</th>
                  {[row.succeeded, row.failed, row.unknown, row.network === 'facebook' ? (facebookViews ?? row.views) : row.views, row.likes, row.comments, row.reposts, row.clicks].map((value, index) => (
                    <td key={index} style={{ padding: '12px 10px', borderBottom: '1px solid var(--border-card)', color: value === null ? 'var(--text-muted)' : undefined }}>
                      {value === null ? <span title="Dados da plataforma ainda indisponíveis">—</span> : value.toLocaleString('pt-BR')}
                    </td>
                  ))}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <section className="analytics-mobile-list" aria-label="Indicadores por rede social">
            {rows.length === 0 && <p className="csp-s-0175">Nenhum resultado disponível para este período.</p>}
            {rows.map((row) => (
              <article className="analytics-mobile-card" key={row.network}>
                <h2>{names[row.network]}</h2>
                <dl>
                  {([
                    ['Envios concluídos', row.succeeded],
                    ['Falhas', row.failed],
                    ['Sem confirmação', row.unknown],
                    ['Visualizações', row.network === 'facebook' ? (facebookViews ?? row.views) : row.views],
                    ['Curtidas', row.likes],
                    ['Comentários', row.comments],
                    ['Reposts', row.reposts],
                    ['Cliques', row.clicks],
                  ] as const).map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value === null
                        ? <span title="Dados da plataforma ainda indisponíveis">—</span>
                        : value.toLocaleString('pt-BR')}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            ))}
          </section>
          <p className="csp-s-0176">
            Envios vêm da fila do Auto Orbital em tempo real. As visualizações do Facebook são da Página conectada, somando somente os dias fornecidos pela Meta na última coleta; não são visualizações individuais dos posts. A coleta de insights ocorre automaticamente após 24 horas quando o serviço está ativo, e na próxima visita após períodos de suspensão do Render Free. O botão permite solicitar outra leitura após 5 minutos. Traço significa indisponível, não zero; curtidas, comentários, reposts e cliques só aparecerão quando houver fonte oficial validada. Redes diferentes não representam pessoas únicas.
          </p>
          {isAdmin && <div className="analytics-probe-actions" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {(['threads', 'facebook', 'instagram'] as const).map((name) => (
              <Button key={name} variant="secondary" size="sm" loading={probing === name} disabled={probing !== null} onClick={() => testInsights(name)}>
                Testar dados de {names[name]}
              </Button>
            ))}
          </div>}
          {visibleProbe && <p role="status" style={{ margin: 0, color: visibleProbe.state === 'ok' ? 'var(--text-body)' : 'var(--negative)' }}>
            {names[visibleProbe.network as Network]}: {visibleProbe.state === 'ok' ? `leitura autorizada (${visibleProbe.result_count} resultado(s))` : visibleProbe.state === 'no_data' ? 'leitura autorizada, sem períodos disponíveis' : visibleProbe.state === 'not_connected' ? 'conta não conectada neste perfil' : visibleProbe.state === 'api_error' ? `API recusou a leitura (HTTP ${visibleProbe.http_status}, código ${visibleProbe.error_code ?? 'não informado'})` : 'não foi possível confirmar a leitura'}.
          </p>}
          {visibleProbe?.network === 'facebook' && visibleProbe.state === 'ok' && facebookViews !== null && (network === 'all' || network === 'facebook') && (
            <section aria-label="Métricas reais da Página do Facebook" className="csp-s-0177">
              <h2 className="csp-s-0178">
                Visualizações da Página do Facebook
              </h2>
              <p className="csp-s-0179">
                <strong>{facebookViews.toLocaleString('pt-BR')}</strong> visualizações nos {visibleProbe.days_returned} período(s) disponibilizados pela Meta.
              </p>
              <p className="csp-s-0180">
                Consulta dos últimos {visibleProbe.days_requested} dias · Métrica page_media_view · Fonte: Meta Graph API.
                Valores iguais a zero são resultados válidos.
              </p>
              <div className="csp-s-0181">
                <table className="csp-s-0182">
                  <thead><tr>
                    <th scope="col" className="csp-s-0183">Período encerrado em (UTC)</th>
                    <th scope="col" className="csp-s-0184">Visualizações</th>
                  </tr></thead>
                  <tbody>{[...(visibleProbe.daily_values ?? [])].reverse().slice(0, 10).map((item) => (
                    <tr key={item.period_end}>
                      <td className="csp-s-0185">
                        {item.period_end.split('-').reverse().join('/')}
                      </td>
                      <td className="csp-s-0186">
                        {item.value.toLocaleString('pt-BR')}
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {(visibleProbe.daily_values?.length ?? 0) > 10 && (
                <p className="csp-s-0187">Exibindo os 10 períodos mais recentes; o total inclui todos os períodos retornados.</p>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
