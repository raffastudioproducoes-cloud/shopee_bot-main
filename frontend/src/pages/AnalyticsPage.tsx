import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
type Summary = { days: number; networks: Row[] }
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
  const userId = useAuthStore((state) => state.user?.id)
  const profileId = useProfileStore((state) => state.activeProfileId)
  // Do not display another account's or another period's previous result.
  const scopeKey = `${userId ?? ''}:${profileId ?? ''}:${days}`
  const visibleProbe = probe?.scopeKey === scopeKey ? probe : null
  const facebookViews = visibleProbe?.network === 'facebook' && visibleProbe.state === 'ok'
    ? visibleProbe.total_views ?? null : null
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', userId, profileId, days, network],
    queryFn: () => api.get<Summary>(`/analytics/summary?days=${days}${network === 'all' ? '' : `&network=${network}`}`),
  })

  const rows = data?.networks ?? []
  const total = rows.reduce((sum, row) => sum + row.succeeded, 0)
  const failures = rows.reduce((sum, row) => sum + row.failed, 0)
  const uncertain = rows.reduce((sum, row) => sum + row.unknown, 0)

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-column)' }}>
      <header>
        <h1 style={{ font: 'var(--text-role-hero)', color: 'var(--text-display)', margin: 0 }}>Análise de redes</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>Resultados das publicações do perfil ativo</p>
      </header>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <Select label="Período" value={days} onChange={(event) => setDays(event.target.value)} width={160} options={[
          { value: '7', label: '7 dias' }, { value: '30', label: '30 dias' }, { value: '90', label: '90 dias' },
        ]} />
        <Select label="Rede" value={network} onChange={(event) => setNetwork(event.target.value)} width={190} options={[
          { value: 'all', label: 'Todas' }, ...Object.entries(names).map(([value, label]) => ({ value, label })),
        ]} />
      </div>

      {isLoading ? <PageSkeleton variant="table" heading={false} /> : error ? (
        <p role="alert" style={{ color: 'var(--negative)' }}>Não foi possível carregar as análises.</p>
      ) : (
        <>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, padding: '16px 0', borderTop: '1px solid var(--border-card)', borderBottom: '1px solid var(--border-card)' }}>
            <span><strong>{total}</strong> envios concluídos</span>
            <span><strong>{failures}</strong> falhas</span>
            <span><strong>{uncertain}</strong> sem confirmação</span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 780, textAlign: 'left' }}>
              <thead><tr>{['Rede', 'Envios concluídos', 'Falhas', 'Sem confirmação', 'Visualizações', 'Curtidas', 'Comentários', 'Reposts', 'Cliques'].map((label) => (
                <th key={label} scope="col" style={{ padding: '12px 10px', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-card)' }}>{label}</th>
              ))}</tr></thead>
              <tbody>{rows.map((row) => (
                <tr key={row.network}>
                  <th scope="row" style={{ padding: '12px 10px', borderBottom: '1px solid var(--border-card)' }}>{names[row.network]}</th>
                  {[row.succeeded, row.failed, row.unknown, row.network === 'facebook' ? facebookViews : row.views, row.likes, row.comments, row.reposts, row.clicks].map((value, index) => (
                    <td key={index} style={{ padding: '12px 10px', borderBottom: '1px solid var(--border-card)', color: value === null ? 'var(--text-muted)' : undefined }}>
                      {value === null ? <span title="Dados da plataforma ainda indisponíveis">—</span> : value.toLocaleString('pt-BR')}
                    </td>
                  ))}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            Envios vêm da fila do Auto Orbital. A visualização do Facebook é da Página conectada, somando somente os dias retornados pela Meta após a consulta manual; não representa visualizações individuais dos posts. Traço significa indisponível, não zero. Contagens de redes diferentes não representam pessoas únicas.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {(['threads', 'facebook', 'instagram'] as const).map((name) => (
              <Button key={name} variant="secondary" size="sm" loading={probing === name} disabled={probing !== null} onClick={() => testInsights(name)}>
                Testar dados de {names[name]}
              </Button>
            ))}
          </div>
          {visibleProbe && <p role="status" style={{ margin: 0, color: visibleProbe.state === 'ok' ? 'var(--text-body)' : 'var(--negative)' }}>
            {names[visibleProbe.network as Network]}: {visibleProbe.state === 'ok' ? `leitura autorizada (${visibleProbe.result_count} resultado(s))` : visibleProbe.state === 'no_data' ? 'leitura autorizada, sem períodos disponíveis' : visibleProbe.state === 'not_connected' ? 'conta não conectada neste perfil' : visibleProbe.state === 'api_error' ? `API recusou a leitura (HTTP ${visibleProbe.http_status}, código ${visibleProbe.error_code ?? 'não informado'})` : 'não foi possível confirmar a leitura'}.
          </p>}
          {visibleProbe?.network === 'facebook' && visibleProbe.state === 'ok' && facebookViews !== null && (network === 'all' || network === 'facebook') && (
            <section aria-label="Métricas reais da Página do Facebook" style={{ padding: 16, border: '1px solid var(--border-card)', borderRadius: 12 }}>
              <h2 style={{ margin: '0 0 8px', font: 'var(--text-role-title)', color: 'var(--text-display)' }}>
                Visualizações da Página do Facebook
              </h2>
              <p style={{ margin: '0 0 4px' }}>
                <strong>{facebookViews.toLocaleString('pt-BR')}</strong> visualizações nos {visibleProbe.days_returned} período(s) disponibilizados pela Meta.
              </p>
              <p style={{ margin: '0 0 12px', color: 'var(--text-muted)' }}>
                Consulta dos últimos {visibleProbe.days_requested} dias · Métrica page_media_view · Fonte: Meta Graph API.
                Valores iguais a zero são resultados válidos.
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', maxWidth: 460, textAlign: 'left' }}>
                  <thead><tr>
                    <th scope="col" style={{ padding: 8, borderBottom: '1px solid var(--border-card)' }}>Período encerrado em (UTC)</th>
                    <th scope="col" style={{ padding: 8, borderBottom: '1px solid var(--border-card)' }}>Visualizações</th>
                  </tr></thead>
                  <tbody>{[...(visibleProbe.daily_values ?? [])].reverse().slice(0, 10).map((item) => (
                    <tr key={item.period_end}>
                      <td style={{ padding: 8, borderBottom: '1px solid var(--border-card)' }}>
                        {item.period_end.split('-').reverse().join('/')}
                      </td>
                      <td style={{ padding: 8, borderBottom: '1px solid var(--border-card)' }}>
                        {item.value.toLocaleString('pt-BR')}
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {(visibleProbe.daily_values?.length ?? 0) > 10 && (
                <p style={{ marginBottom: 0, color: 'var(--text-muted)' }}>Exibindo os 10 períodos mais recentes; o total inclui todos os períodos retornados.</p>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
