import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../api/auth'
import { Panel } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { TextInput } from '../components/ui/TextInput'
import { Modal } from '../components/ui/Modal'
import { Icon } from '../components/ui/Icon'

const bannerStyle = (ok: boolean): React.CSSProperties => ({
  padding: '12px 16px',
  borderRadius: 'var(--r-md)',
  font: 'var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)',
  background: ok ? 'var(--positive-on-glass)' : 'var(--negative-on-glass)',
  color: ok ? 'var(--positive-ink)' : 'var(--negative-ink)',
})

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [forgotOpen, setForgotOpen] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await authApi.login(username, password)
      const user = await authApi.me()
      login('', user)
      navigate({ to: '/' })
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in err) {
        const apiError = err as { status: number; message: string }
        if (apiError.status === 401) {
          setError('Usuário ou senha inválidos')
        } else {
          setError(apiError.message || 'Erro ao fazer login')
        }
      } else {
        setError('Erro inesperado. Tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-app-gradient)',
        padding: 16,
      }}
    >
      <div style={{ width: '100%', maxWidth: 400 }}>
        <Panel surface="glass">
          <div style={{ padding: 32 }}>
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <h1 style={{ font: 'var(--text-role-hero)', margin: 0 }}>Shopee Auto Vendas</h1>
              <p style={{ marginTop: 6, opacity: 0.8 }}>Entre para continuar</p>
            </div>

            {error && <div style={{ ...bannerStyle(false), marginBottom: 20 }}>{error}</div>}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <TextInput
                label="Usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="Digite seu usuário"
                autoComplete="username"
              />

              <label style={{ display: 'block', width: '100%' }}>
                <span
                  style={{
                    display: 'block',
                    font: 'var(--text-role-label)',
                    letterSpacing: 'var(--ls-label)',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    marginBottom: 6,
                  }}
                >
                  Senha
                </span>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="Digite sua senha"
                    autoComplete="current-password"
                    style={{
                      width: '100%',
                      height: 40,
                      padding: '0 44px 0 14px',
                      borderRadius: 'var(--r-md)',
                      background: 'var(--surface-inset)',
                      border: '1px solid var(--border-hairline)',
                      color: 'var(--text-body)',
                      font: 'var(--text-role-body)',
                      outline: 'none',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    style={{
                      position: 'absolute',
                      right: 8,
                      top: '50%',
                      transform: 'translateY(-50%)',
                      display: 'inline-flex',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: 4,
                    }}
                  >
                    <Icon name={showPassword ? 'eye-off' : 'eye'} size={18} />
                  </button>
                </div>
              </label>

              <Button type="submit" variant="primary" fullWidth disabled={loading}>
                {loading ? (
                  <>
                    <Icon name="loader-2" size={18} className="animate-spin" />
                    Entrando...
                  </>
                ) : (
                  'Entrar'
                )}
              </Button>

              <button
                type="button"
                onClick={() => setForgotOpen(true)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  font: 'var(--text-role-body)',
                  textAlign: 'center',
                  cursor: 'pointer',
                  padding: 4,
                }}
              >
                Esqueceu a senha?
              </button>
            </form>
          </div>
        </Panel>
      </div>

      {forgotOpen && (
        <ForgotPasswordModal initialUsername={username} onClose={() => setForgotOpen(false)} />
      )}
    </div>
  )
}

// ── Modal "esqueceu a senha" ────────────────────────────────────────────────────

interface ForgotPasswordModalProps {
  initialUsername: string
  onClose: () => void
}

function ForgotPasswordModal({ initialUsername, onClose }: ForgotPasswordModalProps) {
  const [username, setUsername] = useState(initialUsername)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('As senhas não coincidem')
      return
    }

    setLoading(true)
    try {
      const msg = await authApi.resetPassword(username, newPassword)
      setSuccess(msg || 'Senha atualizada. Faça login com a senha nova.')
      setTimeout(onClose, 1500)
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in err) {
        setError((err as { message: string }).message || 'Erro ao trocar a senha')
      } else {
        setError('Erro inesperado. Tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Trocar senha" width={400}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {error && <div style={bannerStyle(false)}>{error}</div>}
        {success && <div style={bannerStyle(true)}>{success}</div>}

        <TextInput
          label="Usuário"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          disabled={!!success}
        />
        <TextInput
          label="Nova senha"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={!!success}
        />
        <TextInput
          label="Confirmar nova senha"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={!!success}
        />

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !!success}>
            {loading ? 'Trocando...' : 'Trocar senha'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
