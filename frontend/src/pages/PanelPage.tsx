import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { usePostsSearchStore } from '../stores/postsSearchStore'
import { useProductsSearchStore } from '../stores/productsSearchStore'
import { useListsSearchStore } from '../stores/listsSearchStore'
import { searchPageForRoute } from '../lib/pageSearch'
import { authApi } from '../api/auth'
import { ApiError } from '../lib/api'
import { SideRail, type SideRailItem } from '../components/ui/SideRail'
import { TopBar } from '../components/ui/TopBar'
import { IconButton } from '../components/ui/IconButton'
import { NotificationsBell } from '../components/ui/NotificationsBell'
import { ActiveProfileChip } from '../components/profiles/ActiveProfileChip'
import { LocationPermissionNotice } from '../components/profiles/LocationPermissionNotice'
import { Icon } from '../components/ui/Icon'
import { AppFooter } from '../components/layout/AppFooter'
import { PostLoginSplash } from '../components/ui/PostLoginSplash'
import { PageSkeleton } from '../components/ui/Skeleton'
import { PlanBadge } from "../components/plans/PlanSummary"
import { StatusMessage } from '../components/StatusMessage'
import { clearAdminVisitingSite } from '../lib/adminSiteFlag'

const navItems: SideRailItem[] = [
  { value: '/app', label: 'Dashboard', icon: 'house' },
  { value: '/analytics', label: 'Análises', icon: 'chart-no-axes-combined' },
  { value: '/products', label: 'Produtos', icon: 'briefcase' },
  { value: '/lists', label: 'Listas', icon: 'sliders-horizontal' },
  { value: '/posts', label: 'Posts', icon: 'file-text' },
  { value: '/posts/criar', label: 'Criar POST', icon: 'square-pen' },
  { value: '/automacao-posts', label: 'Automação', icon: 'workflow' },
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
  const postsSearch = usePostsSearchStore((state) => state.query)
  const setPostsSearch = usePostsSearchStore((state) => state.setQuery)
  const productsSearch = useProductsSearchStore((state) => state.query)
  const setProductsSearch = useProductsSearchStore((state) => state.setQuery)
  const activeProductsTab = useProductsSearchStore((state) => state.activeTab)
  const listsSearch = useListsSearchStore((state) => state.query)
  const setListsSearch = useListsSearchStore((state) => state.setQuery)
  const searchPage = searchPageForRoute(location.pathname, activeProductsTab)
  const searchValue = searchPage === 'posts' ? postsSearch : searchPage === 'products' ? productsSearch : searchPage === 'lists' ? listsSearch : ''
  const setPageSearch = (query: string) => {
    if (searchPage === 'posts') setPostsSearch(query)
    else if (searchPage === 'products') setProductsSearch(query)
    else if (searchPage === 'lists') setListsSearch(query)
  }
  const { user, login, logout, setUser, isAuthenticated, isRoleVerified, setRoleVerified } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const [authCheckError, setAuthCheckError] = useState(false)
  const [authRetry, setAuthRetry] = useState(0)
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

    // O callback OAuth Google cria o cookie httpOnly e volta para "/";
    // a entrada pública redireciona sessões confirmadas para "/app".
    // Após um logout, o Zustand ainda está deslogado: recuperar a sessão
    // pelo backend antes de decidir que o usuário precisa voltar ao login.
    void authApi.me()
      .then((userData) => {
        if (!active) return
        setAuthCheckError(false)

        // Também evita manter o perfil de outra conta quando o cookie mudou.
        if (!isAuthenticated || user?.id !== userData.id) {
          login(userData)
          return
        }

        setUser(userData)
        setRoleVerified(true)
      })
      .catch((error: unknown) => {
        if (!active) return
        // Somente um 401 confirmado pelo backend invalida a sessão.
        // Erros de rede, 5xx e timeouts preservam cookie e estado local.
        if (error instanceof ApiError && error.status === 401) {
          if (isAuthenticated) logout()
          navigate({ to: '/login' })
          return
        }
        setAuthCheckError(true)
      })

    return () => { active = false }
  }, [isAuthenticated, user?.id, login, navigate, logout, setRoleVerified, setUser, location.pathname, authRetry])

  const authRetryMessage = authCheckError ? (
    <StatusMessage kind="error">
      Não foi possível confirmar a sessão agora. Seus dados foram preservados.{' '}
      <button type="button" onClick={() => { setAuthCheckError(false); setAuthRetry((retry) => retry + 1) }}>
        Tentar novamente
      </button>
    </StatusMessage>
  ) : null

  if (!isAuthenticated || !isRoleVerified) {
    return authRetryMessage ?? <PageSkeleton variant="detail" />
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
      {user?.access !== 'ADMIN' && <PostLoginSplash />}
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
          showSearch={searchPage !== null}
          query={searchValue}
          onQuery={searchPage ? (event) => setPageSearch(event.target.value) : undefined}
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
              <div className="plan-topbar-account">
                <ActiveProfileChip />
                <span className="plan-topbar-tag"><PlanBadge /></span>
              </div>
              <IconButton icon="log-out" label="Sair" tone="glass" onClick={handleLogout} />
            </>
          }
          bell={<NotificationsBell />}
        />

        {authRetryMessage}
        {logoutError && <StatusMessage kind="error" onDismiss={() => setLogoutError(false)}>Não foi possível encerrar a sessão. Tente novamente.</StatusMessage>}
        <main className="csp-s-0313">
          <div key={location.pathname} className="page-enter"><Outlet /></div>
        </main>
        <AppFooter variant="app" />
      </div>

    </div>
  )
}
