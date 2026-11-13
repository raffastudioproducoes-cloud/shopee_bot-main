import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { api } from '../lib/api'
import { getUserTimeZone } from '../lib/userTimeZone'
import { formatMetric } from '../lib/postMetrics'
import type { PostMetricRow } from './PostMetricsPanel'
import { Panel, PanelHeader } from './ui/Panel'
import { Button } from './ui/Button'
import { SkeletonText } from './ui/Skeleton'
import '../styles/post-metrics.css'

const NETWORK_NAMES: Record<string, string> = {
  threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X',
}
type Ranking = {
  posts: PostMetricRow[]
  networks: { network: string; total: number | null; average: number | null; posts_measured: number }[]
}

/** Melhor post e melhor rede em visualizações nos últimos 30 dias, todos os perfis. */
export function DashboardBestPost({ userId }: { userId?: string | number }) {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard-best-post', userId],
    queryFn: () => api.get<Ranking>(`/analytics/ranking?days=30&metric=views&top=1&profile_id=all&tz=${encodeURIComponent(getUserTimeZone())}`),
    enabled: Boolean(userId),
  })
  const best = data?.posts[0]
  const network = data?.networks.find((item) => item.total !== null)
  return <Panel surface="glass">
    <PanelHeader title="Desempenho (30 dias)" />
    <div className="post-metrics-dashboard">
      {isLoading ? <SkeletonText lines={3} />
        : isError ? <p role="alert">Desempenho indisponível no momento.</p>
          : !best ? <p className="post-metrics-muted">Ainda não há visualizações medidas nos últimos 30 dias.</p>
            : <>
              <p><strong>Melhor post:</strong> {formatMetric(best.views)} visualizações · {NETWORK_NAMES[best.network] ?? best.network}</p>
              <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{best.preview}</p>
              {network && <p><strong>Melhor rede:</strong> {NETWORK_NAMES[network.network] ?? network.network} · {formatMetric(network.total)} no total, {formatMetric(network.average)} por post</p>}
            </>}
      <Button variant="secondary" size="sm" onClick={() => navigate({ to: '/analytics' })}>Ver Análises</Button>
    </div>
  </Panel>
}
