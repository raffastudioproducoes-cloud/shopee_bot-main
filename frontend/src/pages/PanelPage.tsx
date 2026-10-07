import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../api/auth'
import { usersApi, type BackupData } from '../api/users'
import { ApiError } from '../lib/api'
import { SideRail, type SideRailItem } from '../components/ui/SideRail'
import { TopBar } from '../components/ui/TopBar'
import { IconButton } from '../components/ui/IconButton'
import { NotificationsBell } from '../components/ui/NotificationsBell'
import { Modal } from '../components/ui/Modal'
import { TextInput } from '../components/ui/TextInput'
import { Button } from '../components/ui/Button'
import { StatusMessage } from '../components/StatusMessage'
import { ConfirmModal } from '../components/profiles/ConfirmModal'
import { ActiveProfileChip } from '../components/profiles/ActiveProfileChip'
import { Icon } from '../components/ui/Icon'

const navItems: SideRailItem[] = [
  { value: '/', label: 'Dashboard', icon: 'house' },
  { value: '/products', label: 'Produtos', icon: 'briefcase' },
  { value: '/lists', label: 'Listas', icon: 'sliders-horizontal' },
  { value: '/posts', label: 'Posts', icon: 'file-text' },
  { value: '/credentials', label: 'Credenciais', icon: 'key-round' },
  { value: '/settings', label: 'Configurações', icon: 'lock' },
  { value: '/ajuda', label: 'Ajuda & FAQ', icon: 'help-circle' },
]

const adminNavItems: SideRailItem[] = [
  { value: '/profiles', label: 'Perfis', icon: 'users' },
  { value: '/logs', label: 'Logs', icon: 'scroll-text' },
]

export function PanelPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, setUser, isAuthenticated } = useAuthStore()
  const [deleteAccountOpen, setDeleteAccountOpen] = useState(false)
  const restoreInputRef = useRef<HTMLInputElement>(null)
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [pendingRestore, setPendingRestore] = useState<File | null>(null)
  const [restoring, setRestoring] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
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

  const items = user?.access === 'ADMIN' ? [...navItems, ...adminNavItems] : navItems

  const handleLogout = () => {
    logout()
    navigate({ to: '/login' })
  }

  const handleExportBackup = async () => {
    try {
      const backup = await usersApi.exportBackup()
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `backup-${backup.exported_at.slice(0, 10)}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setFeedback({ kind: 'error', text: err instanceof ApiError ? err.message : 'Não foi possível exportar o backup.' })
    }
  }

  const handleRestoreFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) setPendingRestore(file)
  }

  const confirmRestore = async () => {
    if (!pendingRestore) return
    setRestoring(true)
    try {
      const data = JSON.parse(await pendingRestore.text()) as BackupData
      const result = await usersApi.restoreBackup(data)
      setFeedback({ kind: 'success', text: result.msg })
    } catch (err) {
      setFeedback({ kind: 'error', text: err instanceof ApiError ? err.message : 'Arquivo de backup inválido ou corrompido.' })
    } finally {
      setRestoring(false)
      setPendingRestore(null)
    }
  }

  return (
    <div className="app-shell">
      <SideRail
        id="app-nav"
        className="app-rail"
        open={menuOpen}
        items={items}
        value={location.pathname}
        onSelect={(value) => {
          setMenuOpen(false)
          navigate({ to: value })
        }}
        brand="SV"
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
              <IconButton icon="download" label="Exportar backup" tone="glass" onClick={handleExportBackup} />
              <IconButton icon="upload" label="Restaurar backup" tone="glass" onClick={() => restoreInputRef.current?.click()} />
              <input
                ref={restoreInputRef}
                type="file"
                accept="application/json"
                onChange={handleRestoreFileChange}
                style={{ display: 'none' }}
              />
              <IconButton icon="trash-2" label="Excluir minha conta" tone="glass" onClick={() => setDeleteAccountOpen(true)} />
              <IconButton icon="log-out" label="Sair" tone="glass" onClick={handleLogout} />
            </>
          }
          bell={<NotificationsBell />}
        />

        {feedback && (
          <StatusMessage kind={feedback.kind} onDismiss={() => setFeedback(null)}>
            {feedback.text}
          </StatusMessage>
        )}

        <main style={{ flex: 1, minWidth: 0 }}>
          <Outlet />
        </main>
      </div>

      {pendingRestore && (
        <ConfirmModal
          title="Restaurar backup"
          confirmLabel="Restaurar"
          busyLabel="Restaurando..."
          loading={restoring}
          onConfirm={confirmRestore}
          onClose={() => setPendingRestore(null)}
        >
          Restaurar este backup vai adicionar os produtos, listas e posts do arquivo à sua conta (não substitui nem apaga nada existente). Continuar?
        </ConfirmModal>
      )}

      {deleteAccountOpen && (
        <DeleteAccountModal
          onClose={() => setDeleteAccountOpen(false)}
          onDeleted={() => {
            logout()
            navigate({ to: '/login' })
          }}
        />
      )}
    </div>
  )
}

// ── Modal de autoexclusão de conta (LGPD/direito ao esquecimento) ──────────────

interface DeleteAccountModalProps {
  onClose: () => void
  onDeleted: () => void
}

function DeleteAccountModal({ onClose, onDeleted }: DeleteAccountModalProps) {
  const [password, setPassword] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await usersApi.deleteSelf(password)
      onDeleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível excluir a conta.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Excluir minha conta" width={420}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <p style={{ color: 'var(--negative-ink)', font: 'var(--text-role-body)', margin: 0 }}>
          Esta ação é irreversível: sua conta e todos os dados associados (credenciais, produtos,
          listas, posts) serão apagados permanentemente.
        </p>

        <TextInput
          label="Confirme sua senha atual *"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, font: 'var(--text-role-body)', color: 'var(--text-muted)' }}>
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
          Tenho certeza que quero excluir minha conta e meus dados permanentemente.
        </label>

        {error && <p role="alert" style={{ color: 'var(--negative-ink)', margin: 0 }}>{error}</p>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={loading || !password.trim() || !confirmed}
            style={{ background: 'var(--red-300)' }}
          >
            {loading ? 'Excluindo...' : 'Excluir conta'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
