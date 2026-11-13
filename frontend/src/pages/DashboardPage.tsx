import { getUserTimeZone } from '../lib/userTimeZone'
import { useNavigate } from '@tanstack/react-router'
import { useDashboard } from '../hooks/useDashboard'
import { StatCard } from '../components/ui/StatCard'
import { Panel, PanelHeader } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import '../components/ui/motion.css'
import type { CSSProperties } from 'react'
import { useTypewriter } from '../lib/motion'
import { Skeleton, SkeletonCard, SkeletonRegion } from '../components/ui/Skeleton'
import { DashboardBestPost } from '../components/DashboardBestPost'
import { useAuthStore } from '../stores/authStore'

function count(value: number | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : '—'
}

function RecordedAt({ value }: { value: string | null }) {
  if (!value || Number.isNaN(Date.parse(value))) return <span>Data indisponível</span>
  return <time dateTime={value}>{new Date(value).toLocaleString('pt-BR', { timeZone: getUserTimeZone() })} ({getUserTimeZone()})</time>
}

const networks: Record<string, string> = { threads: 'Threads', facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok', x: 'X' }
const listStyle = { margin: 0, padding: '0 16px 16px', listStyle: 'none' } as const
const itemStyle = { padding: '12px 0', borderTop: '1px solid var(--border-hairline)', overflowWrap: 'anywhere' } as const

export default function DashboardPage() {
  const navigate = useNavigate()
  const userId = useAuthStore((state) => state.user?.id)
  const { data: stats, isPending, error, refetch } = useDashboard()
  const subtitle = 'Visão geral da sua conta · todos os perfis'
  const typedSubtitle = useTypewriter(subtitle, 'dashboard-subtitulo')

  if (isPending) {
    return (
      <SkeletonRegion><div className="csp-s-0231">
        <div><Skeleton width="180px" height={34} /><Skeleton className="skeleton-sub" width="220px" height={16} /></div>
        <div className="dashboard-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: 'var(--gap-grid)' }}>{[1,2,3,4].map(i => <SkeletonCard key={i} />)}</div>
        <div className="dashboard-content-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 'var(--gap-grid)' }}>{[1,2,3].map(i => <SkeletonCard key={i} />)}</div>
      </div></SkeletonRegion>
    )
  }

  if (error || !stats) {
    return <div role="alert" className="csp-s-0232">
      <p>Não foi possível carregar a visão geral da conta.</p>
      <Button variant="secondary" onClick={() => void refetch()}>Tentar novamente</Button>
    </div>
  }

  return (
    <div className="csp-s-0233">
      <div>
        <h1 className="csp-s-0234">Dashboard</h1>
        <p className="csp-s-0235"><span className="csp-named-sr-only">{subtitle}</span><span aria-hidden="true">{typedSubtitle || '\u00a0'}{typedSubtitle.length < subtitle.length ? <span className="type-caret" /> : null}</span></p>
      </div>

      <div className="dashboard-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: 'var(--gap-grid)' }}>
        <StatCard className="ao-reveal" style={{ "--i": 0 } as CSSProperties} onClick={() => navigate({ to: '/products' })} name="Produtos Cadastrados" icon="briefcase" price={count(stats.products_count)} showSparkline={false} />
        <StatCard className="ao-reveal" style={{ "--i": 1 } as CSSProperties} onClick={() => navigate({ to: '/posts' })} name="Postagens Criadas" icon="file-text" price={count(stats.posts_count)} showSparkline={false} />
        <StatCard className="ao-reveal" style={{ "--i": 2 } as CSSProperties} onClick={() => navigate({ to: '/lists' })} name="Listas de Produtos" icon="sliders-horizontal" price={count(stats.lists_count)} showSparkline={false} />
        <StatCard className="ao-reveal" style={{ "--i": 3 } as CSSProperties} onClick={() => navigate({ to: '/automacao-posts' })} name="Agendamentos" icon="circle-dot" price={count(stats.scheduled_posts)} showSparkline={false} />
      </div>

      <div className="dashboard-content-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 'var(--gap-grid)' }}>
        <Panel surface="glass">
          <PanelHeader title="Postagens recentes" />
          {!Array.isArray(stats.recent_posts) ? <p className="csp-s-0236">Resumo de postagens indisponível.</p> : stats.recent_posts.length === 0 ? <p className="csp-s-0236">Nenhuma postagem ainda.</p> : (
            <ul aria-label="Postagens recentes de todos os perfis" style={listStyle}>
              {stats.recent_posts.map((post) => <li key={post.id} style={itemStyle}>
                <p><strong>#{post.id} · {networks[post.network] ?? post.network}</strong></p>
                <p style={{ whiteSpace: 'pre-wrap' }}>{post.text_preview || 'Publicação sem texto.'}</p>
                <small><RecordedAt value={post.created_at} /></small>
              </li>)}
            </ul>
          )}
        </Panel>

        <Panel surface="dark">
          <PanelHeader title="Atividade recente" />
          {!Array.isArray(stats.recent_activities) ? <p className="csp-s-0237">Resumo de atividades indisponível.</p> : stats.recent_activities.length === 0 ? <p className="csp-s-0237">Nenhuma atividade registrada ainda.</p> : (
            <ul aria-label="Atividades recentes da conta" style={listStyle}>
              {stats.recent_activities.map((activity) => <li key={activity.id} style={itemStyle}>
                <p>{activity.label}</p>
                <small><RecordedAt value={activity.created_at} /></small>
              </li>)}
            </ul>
          )}
        </Panel>

        <DashboardBestPost userId={userId} />

        <Panel surface="dark">
          <PanelHeader title="Ações Rápidas" />
          <p style={{ padding: '0 16px 12px', margin: 0 }}>Posts e listas são criados no perfil ativo.</p>
          <div className="dashboard-quick-actions" style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 16px 16px' }}>
            <Button variant="secondary" icon="briefcase" fullWidth onClick={() => navigate({ to: '/products', search: { action: 'create' } })}>Adicionar Produto</Button>
            <Button variant="secondary" icon="file-text" fullWidth onClick={() => navigate({ to: '/posts/criar' })}>Criar Post</Button>
            <Button variant="secondary" icon="sliders-horizontal" fullWidth onClick={() => navigate({ to: '/lists', search: { action: 'create' } })}>Nova Lista</Button>
          </div>
        </Panel>
      </div>
    </div>
  )
}

