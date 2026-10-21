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
type ProbeResult = { network: string; state: string; metric?: string; result_count?: number; http_status?: number; error_code?: number; error_subcode?: number }

const names: Record<Network, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}

export default function AnalyticsPage() {
  const [days, setDays] = useState('30')
  const [network, setNetwork] = useState('all')
  const [probe, setProbe] = useState<ProbeResult | null>(null)
  const [probing, setProbing] = useState<string | null>(null)
  const userId = useAuthStore((state) => state.user?.id)
  const profileId = useProfileStore((state) => state.activeProfileId)
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
      setProbe(await api.post<ProbeResult>(`/analytics/probe/${name}`, {}))
    } catch {
      setProbe({ network: name, state: 'request_failed' })
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
                  {[row.succeeded, row.failed, row.unknown, row.views, row.likes, row.comments, row.reposts, row.clicks].map((value, index) => (
                    <td key={index} style={{ padding: '12px 10px', borderBottom: '1px solid var(--border-card)', color: value === null ? 'var(--text-muted)' : undefined }}>
                      {value === null ? <span title="Dados da plataforma ainda indisponíveis">—</span> : value.toLocaleString('pt-BR')}
                    </td>
                  ))}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            Envios vêm da fila do Auto Orbital. Métricas de audiência aparecem quando a rede autorizar a leitura; traço não significa zero. Contagens de redes diferentes não representam pessoas únicas.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {(['threads', 'facebook', 'instagram'] as const).map((name) => (
              <Button key={name} variant="secondary" size="sm" loading={probing === name} disabled={probing !== null} onClick={() => testInsights(name)}>
                Testar dados de {names[name]}
              </Button>
            ))}
          </div>
          {probe && <p role="status" style={{ margin: 0, color: probe.state === 'ok' ? 'var(--text-body)' : 'var(--negative)' }}>
            {names[probe.network as Network]}: {probe.state === 'ok' ? `leitura autorizada (${probe.result_count} resultado(s))` : probe.state === 'no_data' ? 'leitura autorizada, sem dados' : probe.state === 'not_connected' ? 'conta não conectada neste perfil' : probe.state === 'api_error' ? `API recusou a leitura (HTTP ${probe.http_status}, código ${probe.error_code ?? 'não informado'})` : 'não foi possível confirmar a leitura'}.
          </p>}
        </>
      )}
    </div>
  )
}
