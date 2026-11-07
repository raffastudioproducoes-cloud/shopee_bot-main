import { useEffect, useState } from 'react'
import { formDraftKey } from '../lib/formDraftStorage'
import { useAutosavedDraft } from '../hooks/useAutosavedDraft'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { useProfileStore } from '../stores/profileStore'
import { profilesApi } from '../api/profiles'
import { Select } from '../components/ui/Select'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'
import { AnalyticsVisuals, type AnalyticsTimeline } from '../components/AnalyticsVisuals'
import { ANALYTICS_NETWORKS, ANALYTICS_RECORDED_NAMES, hasRecordedAnalytics } from '../lib/analyticsNetworks'

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
  posts_with_insights?: number
  posts_with_external_id?: number
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
type RefreshQuota = { unlimited: boolean; used: number; remaining: number | null; limit: number | null; reset_at: string }
type RefreshResult = { state: string; updated_profiles?: number; quota?: RefreshQuota }
type ProbeResult = {
  network: string
  state: string
  metric?: string
  post_count?: number
  total_views?: number | null
}
type ScopedProbe = ProbeResult & { scopeKey: string }
type PostMetric = {
  job_id: string
  network: Network
  profile_id: string | null
  finished_at: string
  preview: string
  state: string
  views: number | null
  likes: number | null
  comments: number | null
  reposts: number | null
  clicks: number | null
  last_completed_at: string | null
}
type PostsResult = { posts: PostMetric[]; total_posts: number; truncated: boolean }

const names = ANALYTICS_RECORDED_NAMES

const metricColumns = [
  { key: 'succeeded', label: 'Envios concluídos' },
  { key: 'failed', label: 'Falhas' },
  { key: 'unknown', label: 'Sem confirmação' },
  { key: 'views', label: 'Visualizações' },
  { key: 'likes', label: 'Curtidas' },
  { key: 'comments', label: 'Comentários' },
  { key: 'reposts', label: 'Reposts' },
  { key: 'clicks', label: 'Cliques' },
] as const

function AnalyticsDetailTable({ rows, selectedProfile, selectedNetwork }: {
  rows: Row[]
  selectedProfile: string
  selectedNetwork: string
}) {
  const recordedRows = new Map(rows.map((row) => [row.network, row]))
  const platforms = ANALYTICS_NETWORKS.filter((item) => selectedNetwork === 'all' || item.key === selectedNetwork)
  const getRow = (key: string) => hasRecordedAnalytics(key) ? recordedRows.get(key) : undefined
  const showMetric = (value: number | null | undefined, detail: string) => value == null
    ? <span title={detail}>—</span>
    : value.toLocaleString('pt-BR')

  return <>
    <div className="analytics-table-heading">
      <h2>Detalhamento por rede</h2>
      <p>{selectedProfile === 'all'
        ? 'Resultados das publicações de todos os perfis da conta'
        : 'Resultados das publicações do perfil selecionado'}</p>
    </div>
    <div className="analytics-desktop-table" style={{ overflowX: 'auto' }}>
      <table className="csp-s-0172">
        <thead><tr><th scope="col" className="csp-s-0173">Rede</th>{metricColumns.map(({ label }) => (
          <th key={label} scope="col" className="csp-s-0173">{label}</th>
        ))}</tr></thead>
        <tbody>{platforms.map((platform) => {
          const row = getRow(platform.key)
          return <tr key={platform.key}>
            <th scope="row" className="csp-s-0174">
              {platform.title}
              <small className={`analytics-detail-status analytics-detail-status--${platform.tone}`} title={platform.detail}>{platform.label}</small>
            </th>
            {metricColumns.map(({ key }) => {
              const value = row?.[key]
              return <td key={key} style={{ padding: '12px 10px', borderBottom: '1px solid var(--border-card)', color: value == null ? 'var(--text-muted)' : undefined }}>
                {showMetric(value, platform.detail)}
              </td>
            })}
          </tr>
        })}</tbody>
      </table>
    </div>
    <section className="analytics-mobile-list" aria-label="Indicadores por rede social">
      {platforms.map((platform) => {
        const row = getRow(platform.key)
        return <article className="analytics-mobile-card" key={platform.key}>
          <h2>{platform.title}</h2>
          <small className={`analytics-detail-status analytics-detail-status--${platform.tone}`} title={platform.detail}>{platform.label}</small>
          <dl>{metricColumns.map(({ key, label }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{showMetric(row?.[key], platform.detail)}</dd>
            </div>
          ))}</dl>
        </article>
      })}
    </section>
    <div className="analytics-detail-note">
      <p className="csp-s-0175">Um traço indica dados indisponíveis, não zero. As redes sem integração aparecem para consulta de cobertura, sem simular envios ou métricas.</p>
    </div>
  </>
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
  const { data: refreshQuota, isLoading: quotaLoading, isError: quotaError } = useQuery({
    queryKey: ['analytics-refresh-quota', userId],
    queryFn: () => api.get<RefreshQuota>('/analytics/refresh/quota'),
    enabled: Boolean(userId),
    refetchOnWindowFocus: true,
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
  const selectedProfileQuery = `&profile_id=${encodeURIComponent(selectedProfile)}`
  const canQuerySelection = selectedProfile === 'all'
    || Boolean(profiles?.some((item) => item.id === selectedProfile))
  const waitingForProfileList = selectedProfile !== 'all' && !profiles && !profilesError
  const filterAvailable = network === 'all' || hasRecordedAnalytics(network)
  const pendingPlatform = filterAvailable ? null : ANALYTICS_NETWORKS.find((item) => item.key === network)
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', userId, selectedProfile, days, network],
    queryFn: () => api.get<Summary>(`/analytics/summary?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const { data: timeline, isLoading: timelineLoading, isError: timelineError } = useQuery({
    queryKey: ['analytics-timeline', userId, selectedProfile, days, network],
    queryFn: () => api.get<AnalyticsTimeline>(`/analytics/timeline?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable,
    retry: 1,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })
  const { data: postsData, isLoading: postsLoading, isError: postsError } = useQuery({
    queryKey: ['analytics-posts', userId, selectedProfile, days, network],
    queryFn: () => api.get<PostsResult>(`/analytics/posts?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const rows = data?.networks ?? []
  const quotaReached = !refreshQuota?.unlimited && refreshQuota?.remaining === 0

  async function refreshAll() {
    if (refreshing || !refreshQuota || quotaReached || !filterAvailable) return
    setRefreshing(true)
    setRefreshMessage(null)
    try {
      const result = await api.post<RefreshResult>(
        `/analytics/refresh?profile_id=${encodeURIComponent(selectedProfile)}`, {}
      )
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['analytics-summary', userId, selectedProfile] }),
        queryClient.invalidateQueries({ queryKey: ['analytics-timeline', userId, selectedProfile] }),
        queryClient.invalidateQueries({ queryKey: ['analytics-posts', userId, selectedProfile] }),
        queryClient.invalidateQueries({ queryKey: ['analytics-refresh-quota', userId] }),
      ])
      setRefreshMessage({
        scope: profileScope,
        message: result.state === 'updated'
          ? `Consulta concluída para ${result.updated_profiles ?? 1} perfil(is). Métricas indisponíveis continuam com traço.`
          : result.state === 'recent'
            ? 'A coleta já está em andamento ou foi solicitada há menos de 5 minutos. A cota não foi consumida.'
            : 'Não foi possível iniciar a atualização agora.',
      })
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        await queryClient.invalidateQueries({ queryKey: ['analytics-refresh-quota', userId] })
      }
      setRefreshMessage({ scope: profileScope, message: error instanceof ApiError && error.status === 429
        ? 'Limite diário atingido. Novas atualizações serão liberadas à meia-noite (Brasília).'
        : 'Falha ao atualizar. Tente novamente em alguns minutos.' })
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
        `/analytics/probe/${name}?profile_id=${encodeURIComponent(selectedProfile)}&days=${days}`, {}
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
          { value: 'all', label: 'Todas' }, ...ANALYTICS_NETWORKS.map((item) => ({ value: item.key, label: item.title })),
        ]} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, justifyContent: 'flex-end' }}>
          <Button variant="secondary" size="sm" loading={refreshing}
            disabled={refreshing || quotaLoading || quotaError || !refreshQuota || quotaReached || waitingForProfileList || !filterAvailable} onClick={refreshAll}>
            Atualizar informações
          </Button>
          <span role="status" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
            {quotaError ? 'Não foi possível consultar a cota'
              : quotaLoading || !refreshQuota ? 'Consultando limite diário...'
                : refreshQuota.unlimited ? 'ADMIN: atualizações ilimitadas'
                  : `${refreshQuota.remaining} de ${refreshQuota.limit} atualizações restantes hoje`}
            {' · '}Automático a cada 24 horas
          </span>
        </div>
      </div>
      {profilesError && <p role="alert" style={{ color: 'var(--negative)', margin: '12px 0 0' }}>
        Não foi possível listar os perfis. A visão geral continua disponível.
      </p>}
      {selectedProfile === 'all' && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
        Os totais incluem o histórico dos perfis arquivados. Métricas são somadas apenas de publicações
        confirmadas do Auto Orbital, sem duplicar IDs externos. A atualização geral coleta os perfis da conta, sem alterar o perfil ativo.
      </p>}

      {refreshMessage?.scope === profileScope && <p role="status" style={{ color: 'var(--text-muted)', margin: '12px 0 0' }}>
        {refreshMessage.message}
      </p>}
      {data?.last_completed_at && <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
        Última consulta às redes: {new Date(data.last_completed_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' })} (Brasília).
      </p>}

      {!filterAvailable ? (
        <>
          <section className="analytics-platform-pending" role="status">
            <h2>{pendingPlatform?.title ?? 'Rede selecionada'} — análises indisponíveis</h2>
            <p>{pendingPlatform?.detail ?? 'Esta rede ainda não possui integração de métricas.'}</p>
            <p>Não há coleta externa habilitada para esta rede. Os dados não são apresentados como zero e nenhuma consulta à API da plataforma é realizada.</p>
          </section>
          <AnalyticsDetailTable rows={[]} selectedProfile={selectedProfile} selectedNetwork={network} />
        </>
      ) : isLoading || waitingForProfileList ? <PageSkeleton variant="table" heading={false} /> : error ? (
        <>
          <p role="alert" className="csp-s-0171">Não foi possível carregar as análises.</p>
          <AnalyticsDetailTable rows={[]} selectedProfile={selectedProfile} selectedNetwork={network} />
        </>
      ) : (
        <>
          <AnalyticsVisuals rows={rows} days={Number(days)} timeline={timeline} posts={postsData?.posts}
            postsLoading={postsLoading} postsError={postsError}
            timelineLoading={timelineLoading} timelineError={timelineError} />
          <AnalyticsDetailTable rows={rows} selectedProfile={selectedProfile} selectedNetwork={network} />
          <div className="analytics-table-heading">
            <h2>Desempenho por publicação</h2>
            <p>Posts enviados pelo Auto Orbital e confirmados pela rede, ordenados por visualizações disponíveis.</p>
          </div>
          {postsLoading ? <p className="csp-s-0176">Carregando desempenho dos posts...</p>
            : postsError ? <p role="alert" className="csp-s-0176">Não foi possível consultar o desempenho por publicação.</p>
              : postsData?.posts.length === 0 ? <p className="csp-s-0176">Nenhuma publicação confirmada neste período.</p>
                : <div className="analytics-performance-table" style={{ overflowX: 'auto', maxWidth: '100%' }}>
                  <table className="csp-s-0172">
                    <thead><tr>{['Publicação', 'Rede', 'Publicado em', 'Visualizações', 'Curtidas', 'Comentários', 'Reposts', 'Cliques', 'Coleta'].map((label) => (
                      <th key={label} scope="col" className="csp-s-0173">{label}</th>
                    ))}</tr></thead>
                    <tbody>{postsData?.posts.map((post) => (
                      <tr key={post.job_id}>
                        <th scope="row" style={{ padding: '12px 10px', maxWidth: 320, minWidth: 210, overflowWrap: 'anywhere' }}>{post.preview || 'Publicação sem texto'}</th>
                        <td>{names[post.network]}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{new Date(post.finished_at).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' })}</td>
                        {[post.views, post.likes, post.comments, post.reposts, post.clicks].map((value, index) => (
                          <td key={index}>{value === null ? <span title="Não disponível para este post">—</span> : value.toLocaleString('pt-BR')}</td>
                        ))}
                        <td>{post.state === 'ok' ? 'Coletado' : post.state === 'multipart_unmapped' ? 'Sequência sem IDs completos' : post.state === 'not_collected' ? 'Aguardando coleta' : post.state === 'missing_external_id' ? 'Sem ID de postagem' : 'Indisponível'}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                  {postsData?.truncated && <p>Exibindo 150 das {postsData.total_posts} publicações. O resumo por rede considera todas.</p>}
                </div>}
          <p className="csp-s-0176">
            Envios vêm da fila do Auto Orbital. Os filtros de 7, 30 ou 90 dias escolhem os posts <strong>publicados nesse intervalo</strong>;
            os insights exibidos são os <strong>totais acumulados de cada post</strong> até a última coleta, não as visualizações ocorridas apenas no intervalo.
            Nunca usamos visualizações gerais do perfil ou da Página. A consulta automática usa o agendamento existente a cada 24 horas; uma consulta manual por perfil pode ser solicitada após 5 minutos.
            Traço significa métrica indisponível, não zero. Facebook e Instagram exigem contas conectadas e uma integração de insights por post validada;
            X e TikTok permanecem indisponíveis para métricas nesta etapa. A atualização manual permite até 10 consultas diárias por conta,
            em qualquer plano, com reset à meia-noite de Brasília; ADMIN tem uso ilimitado. Contas comuns aguardam 5 minutos entre coletas
            do mesmo perfil; ADMIN pode atualizar novamente quando a coleta em andamento for concluída.
          </p>
          {isAdmin && <div className="analytics-probe-actions" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {(['threads', 'facebook', 'instagram'] as const).map((name) => (
              <Button key={name} variant="secondary" size="sm" loading={probing === name}
                disabled={probing !== null || selectedProfile === 'all'} onClick={() => testInsights(name)}>
                Verificar coleta de {names[name]}
              </Button>
            ))}
          </div>}
          {visibleProbe && <p role="status" style={{ margin: 0, color: visibleProbe.state === 'ok' ? 'var(--text-body)' : 'var(--negative)' }}>
            {names[visibleProbe.network as Network]}: {visibleProbe.state === 'ok' ? `métrica de post já coletada (${visibleProbe.total_views ?? '—'} visualizações)` : visibleProbe.state === 'no_posts' ? 'nenhum post confirmado no período' : visibleProbe.state === 'not_collected' ? 'post confirmado, aguardando coleta' : visibleProbe.state === 'missing_external_id' ? 'post sem ID externo para consulta' : 'coleta individual indisponível'}.
          </p>}
        </>
      )}
    </div>
  )
}
