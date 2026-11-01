import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../api/auth'
import { SideRail, type SideRailItem } from '../components/ui/SideRail'
import { TopBar } from '../components/ui/TopBar'
import { IconButton } from '../components/ui/IconButton'
import { NotificationsBell } from '../components/ui/NotificationsBell'
import { ActiveProfileChip } from '../components/profiles/ActiveProfileChip'
import { LocationPermissionNotice } from '../components/profiles/LocationPermissionNotice'
import { Icon } from '../components/ui/Icon'
import { AppFooter } from '../components/layout/AppFooter'
import { PageSkeleton } from '../components/ui/Skeleton'
import { StatusMessage } from '../components/StatusMessage'
import { clearAdminVisitingSite, isAdminVisitingSite } from '../lib/adminSiteFlag'

const navItems: SideRailItem[] = [
  { value: '/', label: 'Dashboard', icon: 'house' },
  { value: '/products', label: 'Produtos', icon: 'briefcase' },
  { value: '/lists', label: 'Listas', icon: 'sliders-horizontal' },
  { value: '/posts', label: 'Posts', icon: 'file-text' },
  { value: '/analytics', label: 'Análises', icon: 'chart-no-axes-combined' },
  { value: '/credentials', label: 'Credenciais', icon: 'key-round' },
  { value: '/profiles', label: 'Perfis', icon: 'users' },
  { value: '/settings', label: 'Configurações', icon: 'lock' },
  { value: '/ajuda', label: 'Ajuda & FAQ', icon: 'help-circle' },
]

const adminNavItems: SideRailItem[] = [
  { value: '/admin', label: 'Painel admin', icon: 'shield-check' },
]

export function PanelPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, login, logout, setUser, isAuthenticated, isRoleVerified, setRoleVerified } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const menuBtnRef = useRef<HTMLButtonElement>(null)

  // Gaveta mobile: fecha com ESC (devolvendo foco ao hambúrguer) e ao trocar de rota.
  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        menuBtnRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    document.querySelector<HTMLButtonElement>('#app-nav .app-rail-item')?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [menuOpen])

  useEffect(() => setMenuOpen(false), [location.pathname])

  useEffect(() => {
    let active = true

    // O callback OAuth Google cria o cookie httpOnly e volta para "/".
    // Após um logout, o Zustand ainda está deslogado: recuperar a sessão
    // pelo backend antes de decidir que o usuário precisa voltar ao login.
    void authApi.me()
      .then((userData) => {
        if (!active) return

        // Também evita manter o perfil de outra conta quando o cookie mudou.
        if (!isAuthenticated || user?.id !== userData.id) {
          login('', userData)
          return
        }

        setUser(userData)
        setRoleVerified(true)
        if (userData.access === 'ADMIN' && location.pathname === '/' && !isAdminVisitingSite()) {
          navigate({ to: '/admin/overview' })
        }
      })
      .catch(() => {
        if (!active) return
        if (isAuthenticated) logout()
        navigate({ to: '/login' })
      })

    return () => { active = false }
  }, [isAuthenticated, user?.id, login, navigate, logout, setRoleVerified, setUser, location.pathname])

  if (!isAuthenticated) {
    return null
  }

  if (!isRoleVerified) {
    return <PageSkeleton variant="detail" />
  }

  const items = user?.access === 'ADMIN' ? [...navItems, ...adminNavItems] : navItems

  const handleLogout = async () => {
    setLogoutError(false)
    try {
      await authApi.logout()
      logout()
      navigate({ to: '/login' })
    } catch {
      setLogoutError(true)
    }
  }

  return (
    <div className="app-shell">
      <LocationPermissionNotice />
      <SideRail
        id="app-nav"
        className="app-rail"
        open={menuOpen}
        items={items}
        value={location.pathname}
        onSelect={(value) => {
          setMenuOpen(false)
          if (value === '/admin') clearAdminVisitingSite()
          navigate({ to: value })
        }}
        logoSrc="/brand/symbol-128.png"
        brand="Auto Orbital"
      />
      <button
        type="button"
        className="app-rail-backdrop"
        data-open={menuOpen ? 'true' : 'false'}
        aria-label="Fechar menu"
        tabIndex={-1}
        onClick={() => setMenuOpen(false)}
      />

      <div className="app-col">
        <TopBar
          query=""
          leading={
            <button
              ref={menuBtnRef}
              type="button"
              className="app-menu-btn"
              aria-label="Abrir menu"
              aria-expanded={menuOpen}
              aria-controls="app-nav"
              onClick={() => setMenuOpen((v) => !v)}
              style={{
                alignItems: 'center',
                justifyContent: 'center',
                width: 44,
                height: 44,
                flex: '0 0 auto',
                borderRadius: 'var(--r-pill)',
                border: 'none',
                background: 'rgba(255,255,255,.14)',
                color: 'var(--text-body)',
                cursor: 'pointer',
              }}
            >
              <Icon name="menu" size={20} />
            </button>
          }
          trailing={
            <>
              <ActiveProfileChip />
              <IconButton icon="log-out" label="Sair" tone="glass" onClick={handleLogout} />
            </>
          }
          bell={<NotificationsBell />}
        />

        {logoutError && <StatusMessage kind="error" onDismiss={() => setLogoutError(false)}>Não foi possível encerrar a sessão. Tente novamente.</StatusMessage>}
        <main className="csp-s-0313">
          <Outlet />
        </main>
        <AppFooter variant="app" />
      </div>

    </div>
  )
}
