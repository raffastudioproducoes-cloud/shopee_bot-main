import { useEffect } from 'react'
import { useNavigate, useLocation, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../api/auth'
import { SideRail, type SideRailItem } from '../components/ui/SideRail'
import { TopBar } from '../components/ui/TopBar'
import { IconButton } from '../components/ui/IconButton'
import { NotificationsBell } from '../components/ui/NotificationsBell'

const navItems: SideRailItem[] = [
  { value: '/', label: 'Dashboard', icon: 'house' },
  { value: '/products', label: 'Produtos', icon: 'briefcase' },
  { value: '/lists', label: 'Listas', icon: 'sliders-horizontal' },
  { value: '/posts', label: 'Posts', icon: 'file-text' },
  { value: '/credentials', label: 'Credenciais', icon: 'key-round' },
]

const adminNavItem: SideRailItem = { value: '/users', label: 'Usuários', icon: 'users' }

export function PanelPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, setUser, isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: '/login' })
      return
    }

    if (!user) {
      authApi.me()
        .then((userData) => {
          setUser(userData)
        })
        .catch(() => {
          logout()
          navigate({ to: '/login' })
        })
    }
  }, [isAuthenticated, navigate, logout, user, setUser])

  const items = user?.access === 'ADMIN' ? [...navItems, adminNavItem] : navItems

  const handleLogout = () => {
    logout()
    navigate({ to: '/login' })
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-app-gradient)' }}>
      <SideRail items={items} value={location.pathname} onSelect={(value) => navigate({ to: value })} brand="SV" />

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minWidth: 0,
          padding: 'var(--shell-pad)',
          gap: 'var(--gap-column)',
        }}
      >
        <TopBar
          query=""
          trailing={<IconButton icon="log-out" label="Sair" tone="glass" onClick={handleLogout} />}
          bell={<NotificationsBell />}
        />

        <main style={{ flex: 1, minWidth: 0 }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
