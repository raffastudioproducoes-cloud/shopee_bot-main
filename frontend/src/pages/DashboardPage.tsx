import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { api } from '../lib/api'
import { StatCard } from '../components/ui/StatCard'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { Skeleton, SkeletonCard, SkeletonRegion } from '../components/ui/Skeleton'

interface DashboardStats {
  products_count: number
  posts_count: number
  lists_count: number
  scheduled_posts: number
}

async function fetchStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/dashboard/stats')
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchStats,
  })

  if (isLoading) {
    return (
      <SkeletonRegion><div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-column)' }}>
        <div><Skeleton width="180px" height={34} /><Skeleton className="skeleton-sub" width="220px" height={16} /></div>
        <div className="dashboard-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--gap-grid)' }}>{[1,2,3,4].map(i => <SkeletonCard key={i} />)}</div>
        <div className="dashboard-content-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 'var(--gap-grid)' }}>{[1,2].map(i => <SkeletonCard key={i} />)}</div>
      </div></SkeletonRegion>
    )
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--negative)' }}>
        Erro ao carregar estatísticas
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-column)' }}>
      <div>
        <h1 style={{ font: 'var(--text-role-hero)', color: 'var(--text-display)', margin: 0 }}>Dashboard</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>Visão geral da sua conta</p>
      </div>

      <div className="dashboard-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--gap-grid)' }}>
        <StatCard name="Produtos Cadastrados" icon="briefcase" price={String(stats?.products_count ?? 0)} showSparkline={false} />
        <StatCard name="Postagens Criadas" icon="file-text" price={String(stats?.posts_count ?? 0)} showSparkline={false} />
        <StatCard name="Listas de Produtos" icon="sliders-horizontal" price={String(stats?.lists_count ?? 0)} showSparkline={false} />
        <StatCard name="Agendados" icon="circle-dot" price={String(stats?.scheduled_posts ?? 0)} showSparkline={false} />
      </div>

      <div className="dashboard-content-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 'var(--gap-grid)' }}>
        <Panel surface="glass">
          <PanelHeader title="Postagens recentes" />
          <div style={{ padding: '0 16px 16px', color: 'var(--text-on-glass-muted)', font: 'var(--text-role-body)' }}>
            Nenhuma postagem ainda.
          </div>
        </Panel>

        <Panel surface="dark">
          <PanelHeader title="Atividade recente" />
          <div style={{ padding: '0 16px 16px', color: 'var(--text-muted)', font: 'var(--text-role-body)' }}>
            Nenhuma atividade registrada ainda.
          </div>
        </Panel>

        <Panel surface="dark">
          <PanelHeader title="Ações Rápidas" />
          <div className="dashboard-quick-actions" style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 16px 16px' }}>
            <Button variant="secondary" icon="briefcase" fullWidth onClick={() => navigate({ to: '/products' })}>
              Adicionar Produto
            </Button>
            <Button variant="secondary" icon="file-text" fullWidth onClick={() => navigate({ to: '/posts' })}>
              Criar Post
            </Button>
            <Button variant="secondary" icon="sliders-horizontal" fullWidth onClick={() => navigate({ to: '/lists' })}>
              Nova Lista
            </Button>
          </div>
        </Panel>
      </div>
    </div>
  )
}
