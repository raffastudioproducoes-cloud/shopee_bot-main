import './LoginPage.css'
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
import { clearAdminVisitingSite } from '../lib/adminSiteFlag'

// Split-screen responsivo: sem breakpoint padrão no projeto (nenhum @media existente
// em frontend/src), então define-se aqui. 768px = ponto de quebra usado no restante
// deste componente (imagem/formulário lado a lado no desktop, empilhados no mobile).

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
      clearAdminVisitingSite()
      login('', user)
      navigate({ to: user.access === 'ADMIN' ? '/admin/overview' : '/' })
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
      
      <div className="login-split">
        <div
          className="login-split__image"
          
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
          
        >
          <div className="csp-login-03">
          <div className="csp-login-04">
            <h1 className="csp-login-05">
              <img src="/brand/wordmark.png" alt="Auto Orbital" className="csp-login-06" />
            </h1>
            <p className="csp-login-07">Entre para continuar</p>
          </div>

          {error && <div className="csp-login-banner csp-login-banner-error csp-login-banner-spaced">{error}</div>}

          <form onSubmit={handleSubmit} className="csp-login-09">
            <TextInput
              label="Usuário"
              icon="user"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Digite seu usuário"
              autoComplete="username"
            />

            <label className="csp-login-10">
              <span
                className="csp-login-11"
              >
                Senha
              </span>
              <div className="csp-login-12">
                <span
                  className="csp-login-13"
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
                  className="csp-login-14"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  className="csp-login-15"
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

            <div className="csp-login-16">
              <button
                type="button"
                onClick={() => setForgotOpen(true)}
                className="csp-login-17"
              >
                Trocar senha
              </button>
              <span className="csp-login-18">·</span>
              <button
                type="button"
                onClick={() => setRegisterOpen(true)}
                className="csp-login-19"
              >
                Criar conta
              </button>
            </div>

            <div className="csp-login-20">
              <div className="csp-login-21" />
              <span className="csp-login-22">
                Ou continue com
              </span>
              <div className="csp-login-23" />
            </div>

            <div className="csp-login-24">
              <span className="csp-login-25" title="Em breve">
                <Button variant="secondary" fullWidth disabled onClick={() => {}} className="csp-login-social-button">
                  Google
                </Button>
              </span>
              <span className="csp-login-27" title="Em breve">
                <Button variant="secondary" fullWidth disabled onClick={() => {}} className="csp-login-social-button">
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
      <form onSubmit={handleSubmit} className="csp-login-29">
        {error && <div className="csp-login-banner csp-login-banner-error">{error}</div>}
        {success && <div className="csp-login-banner csp-login-banner-success">{success}</div>}

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

        <div className="csp-login-30">
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
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!acceptedTerms) { setError('É necessário ler e aceitar os Termos para criar a conta.'); return }
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
      <form onSubmit={handleSubmit} className="csp-login-31">
        {error && <div className="csp-login-banner csp-login-banner-error">{error}</div>}
        {success && <div className="csp-login-banner csp-login-banner-success">{success}</div>}

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

        <div className="csp-login-32">
          <label><input type="checkbox" checked={acceptedTerms} onChange={e=>setAcceptedTerms(e.target.checked)}/> Aceito os <a href="/termos" target="_blank" rel="noreferrer">Termos de Uso</a> e li a <a href="/privacidade" target="_blank" rel="noreferrer">Política de Privacidade</a> e a <a href="/dados-coletados" target="_blank" rel="noreferrer">lista de dados tratados</a>. (Obrigatório)</label>
          <p className="csp-login-33">No primeiro acesso, você poderá escolher se compartilha <strong>uma única localização aproximada</strong> para análise comercial. O navegador pedirá permissão separadamente. Você poderá recusar sem limitar sua conta e excluir o ponto em Configurações.</p>
        </div>
        <div className="csp-login-34">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !!success || !acceptedTerms}>
            {loading ? 'Criando...' : 'Criar conta'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
