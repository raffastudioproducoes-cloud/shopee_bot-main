import { formatInstant, getUserTimeZone } from '../lib/userTimeZone'
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
import { ANALYTICS_NETWORKS, hasRecordedAnalytics } from '../lib/analyticsNetworks'
import { PostMetricsPanel } from '../components/PostMetricsPanel'
import { LEGACY_PERIODS, customRangeError, periodQuery } from '../lib/postMetrics'

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

export default function AnalyticsPage() {
  const [days, setDays] = useState('30')
  const [network, setNetwork] = useState('all')
  const [selectedProfile, setSelectedProfile] = useState('all')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState<{ scope: string; message: string } | null>(null)
  const queryClient = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
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
    days, network, selectedProfile, customFrom, customTo,
  }, (saved) => {
    setCustomFrom(typeof saved?.customFrom === 'string' ? saved.customFrom : '')
    setCustomTo(typeof saved?.customTo === 'string' ? saved.customTo : '')
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
  const selectedProfileQuery = `&profile_id=${encodeURIComponent(selectedProfile)}`
  const canQuerySelection = selectedProfile === 'all'
    || Boolean(profiles?.some((item) => item.id === selectedProfile))
  const waitingForProfileList = selectedProfile !== 'all' && !profiles && !profilesError
  const filterAvailable = network === 'all' || hasRecordedAnalytics(network)
  const pendingPlatform = filterAvailable ? null : ANALYTICS_NETWORKS.find((item) => item.key === network)
  // Resumo operacional legado vai até 90 dias; as métricas por post aceitam até 365 dias.
  const legacyPeriod = LEGACY_PERIODS.includes(days)
  const rangeError = days === 'custom' ? customRangeError(customFrom, customTo) : null
  const metricsPeriod = periodQuery(days, customFrom, customTo, getUserTimeZone())
  const metricsQuery = metricsPeriod
    ? `${metricsPeriod}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`
    : null
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', userId, selectedProfile, days, network],
    queryFn: () => api.get<Summary>(`/analytics/summary?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable && legacyPeriod,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const { data: timeline, isLoading: timelineLoading, isError: timelineError } = useQuery({
    queryKey: ['analytics-timeline', userId, selectedProfile, days, network],
    queryFn: () => api.get<AnalyticsTimeline>(`/analytics/timeline?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable && legacyPeriod,
    retry: 1,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  })
  const { data: postsData, isLoading: postsLoading, isError: postsError } = useQuery({
    queryKey: ['analytics-posts', userId, selectedProfile, days, network],
    queryFn: () => api.get<PostsResult>(`/analytics/posts?days=${days}${network === 'all' ? '' : `&network=${network}`}${selectedProfileQuery}`),
    enabled: Boolean(userId) && canQuerySelection && filterAvailable && legacyPeriod,
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
        queryClient.invalidateQueries({ queryKey: ['post-metrics'] }),
        queryClient.invalidateQueries({ queryKey: ['post-ranking'] }),
        queryClient.invalidateQueries({ queryKey: ['post-series'] }),
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
          { value: '180', label: '180 dias' }, { value: '365', label: '365 dias' }, { value: 'custom', label: 'Personalizado' },
        ]} />
        {days === 'custom' && <>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }}>Início
            <input type="date" value={customFrom} max={customTo || undefined} onChange={(event) => setCustomFrom(event.target.value)} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }}>Fim
            <input type="date" value={customTo} min={customFrom || undefined} onChange={(event) => setCustomTo(event.target.value)} />
          </label>
        </>}
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
      {rangeError && <p role="alert" style={{ color: 'var(--negative)', margin: '12px 0 0' }}>{rangeError} O período personalizado aceita até 365 dias.</p>}
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
        Última consulta às redes: {formatInstant(data.last_completed_at, { dateStyle: 'short', timeStyle: 'short' })} ({getUserTimeZone()}).
      </p>}

      {!filterAvailable ? (
        <>
          <section className="analytics-platform-pending" role="status">
            <h2>{pendingPlatform?.title ?? 'Rede selecionada'} — análises indisponíveis</h2>
            <p>{pendingPlatform?.detail ?? 'Esta rede ainda não possui integração de métricas.'}</p>
            <p>Não há coleta externa habilitada para esta rede. Os dados não são apresentados como zero e nenhuma consulta à API da plataforma é realizada.</p>
          </section>
        </>
      ) : !legacyPeriod ? (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '12px 0 0' }}>
            O resumo de envios por dia cobre até 90 dias. Para períodos maiores, as métricas por postagem abaixo usam o histórico de coletas guardado.
          </p>
          {metricsQuery && canQuerySelection && <PostMetricsPanel query={metricsQuery} scopeKey={profileScope} />}
        </>
      ) : isLoading || waitingForProfileList ? <PageSkeleton variant="table" heading={false} /> : error ? (
        <>
          <p role="alert" className="csp-s-0171">Não foi possível carregar as análises.</p>
        </>
      ) : (
        <>
          <AnalyticsVisuals rows={rows} days={Number(days)} timeline={timeline} posts={postsData?.posts}
            postsLoading={postsLoading} postsError={postsError}
            timelineLoading={timelineLoading} timelineError={timelineError} />
          {metricsQuery && canQuerySelection && <PostMetricsPanel query={metricsQuery} scopeKey={profileScope} />}
          <p className="csp-s-0176">
            Envios vêm da fila do Auto Orbital. Os filtros de período (7 a 365 dias ou personalizado) escolhem os posts <strong>publicados nesse intervalo</strong>;
            os insights exibidos são os <strong>totais acumulados de cada post</strong> até a última coleta, não as visualizações ocorridas apenas no intervalo.
            Nunca usamos visualizações gerais do perfil ou da Página. A consulta automática usa o agendamento existente a cada 24 horas; uma consulta manual por perfil pode ser solicitada após 5 minutos.
            Traço significa métrica indisponível, não zero. Facebook e Instagram exigem contas conectadas e uma integração de insights por post validada;
            X e TikTok permanecem indisponíveis para métricas nesta etapa. A atualização manual permite até 10 consultas diárias por conta,
            em qualquer plano, com reset à meia-noite de Brasília; ADMIN tem uso ilimitado. Contas comuns aguardam 5 minutos entre coletas
            do mesmo perfil; ADMIN pode atualizar novamente quando a coleta em andamento for concluída.
          </p>
        </>
      )}
    </div>
  )
}
