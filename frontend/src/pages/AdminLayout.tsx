import { Link, Outlet, useLocation } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { logsApi } from '../api/logs'
import { Icon } from '../components/ui/Icon'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { SkeletonCard, SkeletonRegion } from '../components/ui/Skeleton'
import '../styles/admin.css'

const sections = [
  { to: '/admin/overview', label: 'Visão geral', icon: 'layout-grid' },
  { to: '/admin/users', label: 'Usuários', icon: 'users' },
  { to: '/admin/logs', label: 'Logs', icon: 'scroll-text' },
  { to: '/admin/credentials', label: 'Diagnóstico', icon: 'key-round' },
] as const

export function AdminLayout() {
  const user = useAuthStore(state => state.user)
  const { pathname } = useLocation()
  const [deskTab, setDeskTab] = useState('recent')
  const [tooltipDismissed, setTooltipDismissed] = useState(false)
  useEffect(() => {
    const dismissTooltip = (event: KeyboardEvent) => { if (event.key === 'Escape') setTooltipDismissed(true) }
    document.addEventListener('keydown', dismissTooltip)
    return () => document.removeEventListener('keydown', dismissTooltip)
  }, [])
  const menuRef = useRef<HTMLElement>(null)
  useLayoutEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const measure = () => {
      const active = menu.querySelector<HTMLElement>('[aria-current="page"]')
      if (!active) return
      menu.style.setProperty('--admin-indicator-x', `${active.offsetLeft}px`)
      menu.style.setProperty('--admin-indicator-width', `${active.offsetWidth}px`)
    }
    measure()
    const observer = new ResizeObserver(measure)
    for (const link of menu.querySelectorAll('a')) observer.observe(link)
    return () => observer.disconnect()
  }, [pathname])
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'recent-logs'],
    queryFn: () => logsApi.list({ limit: 3 }),
    refetchInterval: 60_000,
  })

  return (
    <div className="admin-shell">
      <a className="admin-skip" href="#admin-content">Ir para o conteúdo</a>
      <div className="admin-frame">
      <header className="admin-header">
        <Link to="/admin/overview" className="admin-brand" aria-label="Auto Orbital, administração">
          <img src="/brand/symbol-128.png" alt="" width="36" height="36" />
          <span>Auto Orbital <small>ADMIN</small></span>
        </Link>
        <nav ref={menuRef} className="admin-menu" aria-label="Administração">
          <span className="admin-menu-indicator" aria-hidden="true" />
          {sections.map(section => {
            const active = pathname === section.to
            return (
              <Link key={section.to} to={section.to} className={`admin-menu-link${active ? ' is-active' : ''}`} aria-label={section.label} aria-current={active ? 'page' : undefined} title={section.label}>
                <Icon name={section.icon} size={16} />
                <span>{section.label}</span>
              </Link>
            )
          })}
        </nav>
        <div className="admin-account">
          <span className="admin-account-icon"><Icon name="user" size={16} /></span>
          <span><strong>{user?.username}</strong><small>Administrador</small></span>
        </div>
      </header>

      <div className="admin-workspace">
        <nav className="admin-utilities" aria-label="Ferramentas administrativas">
          {sections.map(section => <Link key={section.to} to={section.to} aria-label={section.label} title={section.label}><Icon name={section.icon} size={16} /></Link>)}
        </nav>
        <main id="admin-content" className="admin-content" tabIndex={-1}><div className="admin-route" key={pathname}><Outlet /></div></main>
        <aside className="admin-desk" aria-label="Central administrativa">
          <div className="admin-desk-heading"><h2>Central administrativa</h2><p>Acesso e atividade do aplicativo.</p></div>
          <div className="admin-desk-tabs" role="group" aria-label="Painel de apoio">
            {[["recent", "Atividade"], ["links", "Atalhos"]].map(([value, label]) => <button key={value} type="button" aria-pressed={deskTab === value} onClick={() => setDeskTab(value)}>{label}</button>)}
            <Link to="/admin/logs">Auditoria</Link>
          </div>
          {deskTab === 'recent' && <>
            {isLoading ? <SkeletonRegion><SkeletonCard /></SkeletonRegion> : error ? (
              <p role="alert">Não foi possível carregar a atividade.</p>
            ) : data?.data.length ? (
              <ol className="admin-activity">
                {data.data.map(entry => <li key={entry.id}>
                  <Panel surface="dark" className="admin-event-card" style={{ padding: 14 }}>
                    <div className="admin-event-meta"><Badge tone="neutral">{entry.method}</Badge><time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}</time></div>
                    <h3>{entry.action || 'Requisição registrada'}</h3>
                    <p className="admin-event-path">Registro operacional</p>
                    <Link to="/admin/logs" className="admin-event-footer"><Icon name="clock" size={13} /><span>{new Date(entry.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })} · {entry.status_code ?? '—'}</span><Icon name="arrow-up-right" size={14} /></Link>
                  </Panel>
                </li>)}
              </ol>
            ) : <p className="admin-muted">Nenhuma atividade registrada.</p>}
          </>}
          {deskTab === 'links' && <Panel surface="dark" style={{ padding: 16 }}>
            <h3 className="admin-section-title">Acesso rápido</h3>
            <div className="admin-shortcuts">
              {sections.map(section => <Link key={section.to} to={section.to}><Icon name={section.icon} size={17} /><span>{section.label}</span><Icon name="chevron-right" size={15} /></Link>)}
            </div>
          </Panel>}
        </aside>
      </div>
      <nav className={`admin-dock${tooltipDismissed ? ' is-tooltip-dismissed' : ''}`} aria-label="Atalhos administrativos">
        {sections.map((shortcut, index) => <Link key={shortcut.to} to={shortcut.to} aria-label={shortcut.label} aria-current={pathname === shortcut.to ? 'page' : undefined} onPointerEnter={() => setTooltipDismissed(false)} onFocus={() => setTooltipDismissed(false)} className={`admin-dock-link admin-dock-link--${index}`}>
          <span className="admin-dock-tooltip" aria-hidden="true">{shortcut.label}</span>
          <span className="admin-dock-icon"><Icon name={shortcut.icon} size={16} /></span>
        </Link>)}
      </nav>
      </div>
    </div>
  )
}
