import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { api } from '../lib/api'
import { StatCard } from '../components/ui/StatCard'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'

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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256, color: 'var(--text-muted)' }}>
        Carregando...
      </div>
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

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--gap-grid)' }}>
        <StatCard name="Produtos Cadastrados" icon="briefcase" price={String(stats?.products_count ?? 0)} showSparkline={false} />
        <StatCard name="Postagens Criadas" icon="file-text" price={String(stats?.posts_count ?? 0)} showSparkline={false} />
        <StatCard name="Listas de Produtos" icon="sliders-horizontal" price={String(stats?.lists_count ?? 0)} showSparkline={false} />
        <StatCard name="Agendados" icon="circle-dot" price={String(stats?.scheduled_posts ?? 0)} showSparkline={false} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--gap-grid)' }}>
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 16px 16px' }}>
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
