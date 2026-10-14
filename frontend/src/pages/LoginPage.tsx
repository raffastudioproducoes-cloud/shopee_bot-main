import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../api/auth'
import { Button } from '../components/ui/Button'
import { TextInput } from '../components/ui/TextInput'
import { Modal } from '../components/ui/Modal'
import { Icon } from '../components/ui/Icon'
import { AppFooter } from '../components/layout/AppFooter'

// Split-screen responsivo: sem breakpoint padrão no projeto (nenhum @media existente
// em frontend/src), então define-se aqui. 768px = ponto de quebra usado no restante
// deste componente (imagem/formulário lado a lado no desktop, empilhados no mobile).
const splitScreenStyles = `
  .login-page { display: flex; flex-direction: column; min-height: 100vh; min-height: 100dvh; background: var(--bg-app); }
  .login-split { display: flex; flex: 1; flex-direction: column; min-height: 0; }
  .login-split__image { width: 100%; height: 38vh; position: relative; overflow: hidden; }
  /* max-width:none derruba o preflight do Tailwind (img,video{max-width:100%}), que
     senão prende a largura do vídeo aos 45% do container pai mesmo com width:80vw. */
  .login-split__video { position: absolute; inset: 0; width: 100%; height: 100%; max-width: none; object-fit: cover; object-position: center; }
  .login-split__fade { position: absolute; left: 0; right: 0; bottom: 0; height: 30%; background: linear-gradient(to bottom, transparent 0%, var(--bg-app) 85%); pointer-events: none; }
  .login-split__form { width: 100%; flex: 1; display: flex; align-items: center; justify-content: center; padding: 32px 16px; }
  @media (min-width: 768px) {
    .login-split { flex-direction: row; }
    /* Largura/posição do painel de imagem no fluxo flex NÃO mudam (continua 45%) —
       é isso que garante que .login-split__form (55%, via flex-grow) fique no mesmo
       lugar de sempre. O vídeo por dentro é que se estende visualmente até 80vw via
       position:absolute + overflow:visible no painel pai (ver .login-split__video). */
    .login-split__image { width: 45%; height: auto; overflow: visible; z-index: 0; }
    .login-split__video { top: 0; left: 0; right: auto; bottom: auto; width: 80vw; height: 100%; }
    .login-split__fade { display: none; }
    .login-split__form { width: 55%; height: auto; z-index: 1; }
  }
`

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
  const [registerOpen, setRegisterOpen] = useState(false)
  // ponytail: checagem única no mount, sem listener de mudança ao vivo — se o usuário
  // alternar a preferência do SO com a tela aberta, precisaria recarregar a página.
  const [prefersReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

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
    <div className="login-page">
      <style>{splitScreenStyles}</style>

      <div className="login-split">
        <div
          className="login-split__image"
          style={{
            // Camada de baixo: fica visível se o vídeo falhar ao carregar ou se o usuário
            // preferir menos movimento — nunca sobra um buraco vazio/branco.
            background: 'linear-gradient(160deg, var(--surface-card) 0%, var(--bg-app) 100%)',
          }}
        >
          {!prefersReducedMotion && (
            <video className="login-split__video" src="/videos/login-bg.mp4" autoPlay loop muted playsInline />
          )}
          {/* Fusão vídeo→form no mobile (empilhado): degradê na borda inferior do painel de
              vídeo. Escondido no desktop via CSS (lá quem funde é o background do form). */}
          <div className="login-split__fade" />
        </div>

        <div
          className="login-split__form"
          style={{ background: 'linear-gradient(to right, transparent 0%, var(--bg-app) 55%)' }}
        >
          <div style={{ width: '100%', maxWidth: 360 }}>
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <h1 style={{ font: 'var(--text-role-hero)', margin: 0 }}>
              <img src="/brand/wordmark.png" alt="Auto Orbital" style={{ height: 44, width: 'auto', maxWidth: '100%', display: 'block', margin: '0 auto' }} />
            </h1>
            <p style={{ marginTop: 6, opacity: 0.8 }}>Entre para continuar</p>
          </div>

          {error && <div style={{ ...bannerStyle(false), marginBottom: 20 }}>{error}</div>}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <TextInput
              label="Usuário"
              icon="user"
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
                <span
                  style={{
                    position: 'absolute',
                    left: 14,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    display: 'inline-flex',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                >
                  <Icon name="lock" size={16} />
                </span>
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
                    padding: '0 44px 0 40px',
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

            <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
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
                Trocar senha
              </button>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <button
                type="button"
                onClick={() => setRegisterOpen(true)}
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
                Criar conta
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0' }}>
              <div style={{ flex: 1, height: 1, background: 'var(--border-hairline)' }} />
              <span style={{ font: 'var(--text-role-label)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                Ou continue com
              </span>
              <div style={{ flex: 1, height: 1, background: 'var(--border-hairline)' }} />
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <span style={{ flex: 1 }} title="Em breve">
                <Button variant="secondary" fullWidth disabled onClick={() => {}} style={{ border: '1px solid var(--border-hairline)' }}>
                  Google
                </Button>
              </span>
              <span style={{ flex: 1 }} title="Em breve">
                <Button variant="secondary" fullWidth disabled onClick={() => {}} style={{ border: '1px solid var(--border-hairline)' }}>
                  Apple
                </Button>
              </span>
            </div>
          </form>
          </div>
        </div>
      </div>

      <AppFooter variant="login" />

      {forgotOpen && (
        <ForgotPasswordModal initialUsername={username} onClose={() => setForgotOpen(false)} />
      )}

      {registerOpen && <RegisterModal onClose={() => setRegisterOpen(false)} />}
    </div>
  )
}

// ── Modal "trocar senha" (exige senha atual — não é recuperação de conta) ──────

interface ForgotPasswordModalProps {
  initialUsername: string
  onClose: () => void
}

function ForgotPasswordModal({ initialUsername, onClose }: ForgotPasswordModalProps) {
  const [username, setUsername] = useState(initialUsername)
  const [currentPassword, setCurrentPassword] = useState('')
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
      const msg = await authApi.resetPassword(username, currentPassword, newPassword)
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
          label="Senha atual"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
          autoComplete="current-password"
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

// ── Modal "criar conta" ─────────────────────────────────────────────────────────

interface RegisterModalProps {
  onClose: () => void
}

function RegisterModal({ onClose }: RegisterModalProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('As senhas não coincidem')
      return
    }

    setLoading(true)
    try {
      await authApi.register(username, password)
      setSuccess('Conta criada! Faça login.')
      setTimeout(onClose, 1500)
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in err) {
        setError((err as { message: string }).message || 'Erro ao criar conta')
      } else {
        setError('Erro inesperado. Tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Criar conta" width={400}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {error && <div style={bannerStyle(false)}>{error}</div>}
        {success && <div style={bannerStyle(true)}>{success}</div>}

        <TextInput
          label="Usuário"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
          disabled={!!success}
        />
        <TextInput
          label="Senha"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={!!success}
        />
        <TextInput
          label="Confirmar senha"
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
            {loading ? 'Criando...' : 'Criar conta'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
