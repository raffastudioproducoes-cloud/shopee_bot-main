import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { TrendingUp, Package, FileText, List, Loader2 } from 'lucide-react'

interface DashboardStats {
  products_count: number
  posts_count: number
  lists_count: number
  scheduled_posts: number
}

async function fetchStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/dashboard/stats')
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number; icon: React.ComponentType<{ className?: string }>; color: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-gray-500">{title}</CardTitle>
        <Icon className={`w-5 h-5 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchStats,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-600">
        Erro ao carregar estatísticas
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Visão geral da sua conta</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Produtos"
          value={stats?.products_count || 0}
          icon={Package}
          color="text-blue-500"
        />
        <StatCard
          title="Posts"
          value={stats?.posts_count || 0}
          icon={FileText}
          color="text-green-500"
        />
        <StatCard
          title="Listas"
          value={stats?.lists_count || 0}
          icon={List}
          color="text-purple-500"
        />
        <StatCard
          title="Agendados"
          value={stats?.scheduled_posts || 0}
          icon={TrendingUp}
          color="text-orange-500"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Atividade Recente</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-500 text-sm">Nenhuma atividade recente</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Ações Rápidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link to="/products" className="block">
              <button className="w-full flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                <Package className="w-5 h-5 text-primary" />
                <span className="font-medium">Adicionar Produto</span>
              </button>
            </Link>
            {/* skipped: rota /posts (Fase 5, ainda não migrada) */}
            <Link to="/lists" className="block">
              <button className="w-full flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                <List className="w-5 h-5 text-purple-500" />
                <span className="font-medium">Nova Lista</span>
              </button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}