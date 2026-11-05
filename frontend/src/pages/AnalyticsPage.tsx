import { useEffect, useState } from 'react'
import { formDraftKey } from '../lib/formDraftStorage'
import { useAutosavedDraft } from '../hooks/useAutosavedDraft'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { useProfileStore } from '../stores/profileStore'
import { profilesApi } from '../api/profiles'
import { Select } from '../components/ui/Select'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'
import { AnalyticsVisuals, type AnalyticsTimeline } from '../components/AnalyticsVisuals'

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
  const [selectedProfile, setSelectedProfile] = useState('all')
  const [probe, setProbe] = useState<ScopedProbe | null>(null)
  const [probing, setProbing] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState<{ scope: string; message: string } | null>(null)
  const queryClient = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
  const isAdmin = useAuthStore((state) => state.user?.access === 'ADMIN')
  const profileId = useProfileStore((state) => state.activeProfileId)
  const { data: profiles, isError: profilesError } = useQuery({
    queryKey: ['analytics-profiles', userId],
    queryFn: profilesApi.list,
    enabled: Boolean(userId),
  })
  // Keep the existing saved period/network filters per operational profile.
  // The viewing selector never calls setActiveProfileId or /profiles/.../activate.
  useAutosavedDraft(formDraftKey(userId, 'analytics-filters', profileId), {
    days, network, selectedProfile,
  }, (saved) => {
    setDays(typeof saved?.days === 'string' ? saved.days : '30')
    setNetwork(typeof saved?.network === 'string' ? saved.network : 'all')
    setSelectedProfile(typeof saved?.selectedProfile === 'string' ? saved.selectedProfile : 'all')
  })
  useEffect(() => {
    // A removed/archived profile cannot stay selected after the list is reloaded.
    if (selectedProfile !== 'all' && (profilesError || (
      profiles && !profiles.some((item) => item.id === selectedProfile)
    ))) {
      setSelectedProfile('all')
    }
  }, [profiles, profilesError, selectedProfile])
  // Do not display another account's or another period's previous result.
  const profileScope = `${userId ?? ''}:${selectedProfile}`
  const scopeKey = `${profileScope}:${days}`
  const visibleProbe = isAdmin && selectedProfile !== 'all' && probe?.scopeKey === scopeKey ? probe : null
  const facebookViews = visibleProbe?.network === 'facebook' && visibleProbe.state === 'ok'
    ? visibleProbe.total_views ?? null : null
  const selectedProfileQuery = `&profile_id=${encodeURIComponent(selectedProfile)}`
  const canQuerySelection = selectedProfile === 'all'
    || Boolean(profiles?.some((item) => item.id === selectedProfile))
  const waitingForProfileList = selectedProfile !== 'all' && !profiles && !profilesError
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', userId, selectedProfile, days, network],
    queryFn: () => api.get<Summary>(`/analytics/summary?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const { data: timeline, isLoading: timelineLoading, isError: timelineError } = useQuery({
    queryKey: ['analytics-timeline', userId, selectedProfile, days, network],
    queryFn: () => api.get<AnalyticsTimeline>(`/analytics/timeline?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection,
    retry: 1,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const rows = data?.networks ?? []

  async function refreshAll() {
    if (selectedProfile === 'all' || refreshing) return
    setRefreshing(true)
    setRefreshMessage(null)
    try {
      const result = await api.post<RefreshResult>(
        `/analytics/refresh?profile_id=${encodeURIComponent(selectedProfile)}`, {}
      )
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['analytics-summary', userId, selectedProfile] }),
        queryClient.invalidateQueries({ queryKey: ['analytics-timeline', userId, selectedProfile] }),
      ])
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
    if (selectedProfile === 'all') return
    setProbing(name)
    setProbe(null)
    try {
      const result = await api.post<ProbeResult>(
        `/analytics/probe/${name}?profile_id=${encodeURIComponent(selectedProfile)}${name === 'facebook' ? `&days=${days}` : ''}`, {}
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
        <p className="csp-s-0170">{selectedProfile === 'all'
          ? 'Resultados das publicações de todos os perfis da conta'
          : 'Resultados das publicações do perfil selecionado'}</p>
      </header>

      <div className="analytics-filters" style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <Select label="Perfil" value={selectedProfile} onChange={(event) => setSelectedProfile(event.target.value)}
          width={220} options={[
            { value: 'all', label: 'Todos os perfis' },
            ...(profiles ?? []).map((item) => ({
              value: item.id, label: `${item.nome || 'Perfil'}${item.kind === 'principal' ? ' (principal)' : ''}`,
            })),
          ]} />
        <Select label="Período" value={days} onChange={(event) => setDays(event.target.value)} width={160} options={[
          { value: '7', label: '7 dias' }, { value: '30', label: '30 dias' }, { value: '90', label: '90 dias' },
        ]} />
        <Select label="Rede" value={network} onChange={(event) => setNetwork(event.target.value)} width={190} options={[
          { value: 'all', label: 'Todas' }, ...Object.entries(names).map(([value, label]) => ({ value, label })),
        ]} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, justifyContent: 'flex-end' }}>
          <Button variant="secondary" size="sm" loading={refreshing} disabled={refreshing || selectedProfile === 'all'} onClick={refreshAll}>
            Atualizar informações
          </Button>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Automático a cada 24 horas</span>
        </div>
      </div>
      {profilesError && <p role="alert" style={{ color: 'var(--negative)', margin: '12px 0 0' }}>
        Não foi possível listar os perfis. A visão geral continua disponível.
      </p>}
      {selectedProfile === 'all' && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
        Os totais incluem o histórico dos perfis arquivados. Insights oficiais e atualização de redes
        são individuais: selecione um perfil para consultá-los sem duplicar métricas.
      </p>}

      {refreshMessage?.scope === profileScope && <p role="status" style={{ color: 'var(--text-muted)', margin: '12px 0 0' }}>
        {refreshMessage.message}
      </p>}
      {data?.last_completed_at && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
        Última consulta às redes: {new Date(data.last_completed_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' })} (Brasília).
      </p>}

      {isLoading || waitingForProfileList ? <PageSkeleton variant="table" heading={false} /> : error ? (
        <p role="alert" className="csp-s-0171">Não foi possível carregar as análises.</p>
      ) : (
        <>
          <AnalyticsVisuals rows={rows} days={Number(days)} timeline={timeline}
            timelineLoading={timelineLoading} timelineError={timelineError} />
          <div className="analytics-table-heading">
            <h2>Detalhamento por rede</h2>
            <p>{selectedProfile === 'all'
              ? 'Contagens operacionais de todos os perfis da conta'
              : 'Dados oficiais disponíveis e contagens operacionais do perfil selecionado'}</p>
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
            Envios vêm da fila do Auto Orbital em tempo real. {selectedProfile === 'all'
              ? 'Na visão geral, visualizações e outros insights oficiais não são somados entre perfis, porque páginas conectadas podem coincidir; por isso aparecem como indisponíveis.'
              : 'As visualizações do Facebook são da Página conectada, somando somente os dias fornecidos pela Meta na última coleta; não são visualizações individuais dos posts.'}{' '}
            A coleta de insights ocorre automaticamente após 24 horas quando o serviço está ativo, e na próxima visita após períodos de suspensão do Render Free. O botão permite solicitar outra leitura após 5 minutos quando um perfil está selecionado. Traço significa indisponível, não zero; curtidas, comentários, reposts e cliques só aparecerão quando houver fonte oficial validada. Redes diferentes não representam pessoas únicas.
          </p>
          {isAdmin && <div className="analytics-probe-actions" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {(['threads', 'facebook', 'instagram'] as const).map((name) => (
              <Button key={name} variant="secondary" size="sm" loading={probing === name}
                disabled={probing !== null || selectedProfile === 'all'} onClick={() => testInsights(name)}>
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
