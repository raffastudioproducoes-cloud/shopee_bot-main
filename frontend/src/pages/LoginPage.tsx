import './LoginPage.css'
import { useEffect, useState } from 'react'
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
import { validatePassword } from '../lib/password'
import { validCpf } from '../lib/cpf'
import { PasswordRecoveryRequestModal } from '../components/auth/PasswordRecoveryRequestModal'

// Split-screen responsivo: sem breakpoint padrão no projeto (nenhum @media existente
// em frontend/src), então define-se aqui. 768px = ponto de quebra usado no restante
// deste componente (imagem/formulário lado a lado no desktop, empilhados no mobile).

type RecoveryLinkState = { token: string | null; notice: string }

/** O Supabase entrega o token de recuperação no fragmento, nunca ao servidor web.
 *  Removemos esse fragmento imediatamente do histórico antes de exibir o modal. */
function readRecoveryLink(): RecoveryLinkState {
  if (typeof window === 'undefined') return { token: null, notice: '' }
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const token = params.get('access_token')
  const type = params.get('type')
  const isAuthResponse = params.has('access_token') || params.has('error') || params.has('type')
  if (isAuthResponse) {
    window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search)
  }
  if (type === 'recovery') {
    return token
      ? { token, notice: '' }
      : { token: null, notice: 'Link de recuperação inválido. Solicite um novo e-mail.' }
  }
  if (params.has('error')) {
    return { token: null, notice: 'O link de confirmação expirou ou é inválido. Solicite outro.' }
  }
  if (type === 'signup' || type === 'email') {
    return { token: null, notice: 'E-mail confirmado. Agora entre com seu e-mail e senha.' }
  }
  return { token: null, notice: '' }
}

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
  const [recoveryLink, setRecoveryLink] = useState(readRecoveryLink)
  const [notice, setNotice] = useState(recoveryLink.notice)
  const [capabilities, setCapabilities] = useState({ email_enabled: false, email_signup_enabled: false, google_enabled: false, legacy_support_enabled: false })
  const [googleSetupOpen, setGoogleSetupOpen] = useState(
    () => typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('google_setup') === '1'
  )

  useEffect(() => {
    void authApi.capabilities().then(setCapabilities).catch(() => {
      setCapabilities({ email_enabled: false, email_signup_enabled: false, google_enabled: false, legacy_support_enabled: false })
    })
    if (new URLSearchParams(window.location.search).has('google_error')) {
      setError('Não foi possível autorizar a conta Google. Tente novamente.')
    }
  }, [])
  // ponytail: checagem única no mount, sem listener de mudança ao vivo — se o usuário
  // alternar a preferência do SO com a tela aberta, precisaria recarregar a página.
  const [prefersReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  // O backend restringe o login legado ao username de suporte explicitamente configurado.
  // Se Supabase Auth estiver desativado em ambiente local, preserva o login legado original.
  const useLegacyLogin = !capabilities.email_enabled ||
    (capabilities.legacy_support_enabled && !username.trim().includes('@'))
  const loginFieldLabel = !capabilities.email_enabled
    ? 'Usuário'
    : capabilities.legacy_support_enabled ? 'E-mail ou usuário de suporte' : 'E-mail'
  const loginFieldType = !capabilities.email_enabled || capabilities.legacy_support_enabled ? 'text' : 'email'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (useLegacyLogin) {
        await authApi.login(username.trim(), password)
      } else {
        await authApi.loginEmail(username.trim(), password)
      }
      const user = await authApi.me()
      clearAdminVisitingSite()
      login('', user)
      navigate({ to: user.access === 'ADMIN' ? '/admin/overview' : '/app' })
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in err) {
        const apiError = err as { status: number; message: string }
        if (apiError.status === 401) {
          setError(useLegacyLogin
            ? 'Usuário ou senha inválidos'
            : 'E-mail ou senha inválidos')
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

          {error && <div role="alert" className="csp-login-banner csp-login-banner-error csp-login-banner-spaced">{error}</div>}
          {notice && <div role="status" className="csp-login-banner csp-login-banner-success csp-login-banner-spaced">{notice}</div>}

          <form onSubmit={handleSubmit} className="csp-login-09">
            <TextInput
              label={loginFieldLabel}
              icon="user"
              type={loginFieldType}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder={capabilities.legacy_support_enabled ? 'Seu e-mail ou usuário de suporte' : capabilities.email_enabled ? 'Digite seu e-mail' : 'Digite seu usuário'}
              autoComplete="username"
            />
            {capabilities.legacy_support_enabled && (
              <p className="login-support-hint">Para suporte Shopee, use o nome de usuário sem @. Não é necessário selecionar outro modo de login.</p>
            )}

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
                disabled={Boolean(username.trim()) && useLegacyLogin}
                className="csp-login-17"
              >
                Esqueci minha senha
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
              <span className="csp-login-25" title={capabilities.google_enabled ? "Entrar com Google" : "Aguardando configuração Google"}>
                <Button variant="secondary" fullWidth disabled={!capabilities.google_enabled}
                  onClick={() => { window.location.assign('/api/auth/supabase/google/authorize') }}
                  className="csp-login-social-button">
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
        <PasswordRecoveryRequestModal initialEmail={username.includes('@') ? username : ''} onClose={() => setForgotOpen(false)} />
      )}

      {registerOpen && <RegisterModal enabled={capabilities.email_signup_enabled} onClose={() => setRegisterOpen(false)} />}
      {recoveryLink.token && (
        <PasswordRecoveryFinishModal
          accessToken={recoveryLink.token}
          onClose={() => setRecoveryLink({ token: null, notice: '' })}
          onSuccess={(message) => {
            setRecoveryLink({ token: null, notice: '' })
            setNotice(message)
          }}
        />
      )}
      {googleSetupOpen && (
        <GoogleSetupModal
          onClose={() => {
            setGoogleSetupOpen(false)
            window.history.replaceState({}, '', '/login')
          }}
          onSuccess={async () => {
            const user = await authApi.me()
            clearAdminVisitingSite()
            login('', user)
            setGoogleSetupOpen(false)
            navigate({ to: user.access === 'ADMIN' ? '/admin/overview' : '/app' })
          }}
        />
      )}
    </div>
  )
}

// ── Modal aberto somente após o link de recuperação autorizado pelo Supabase ──

function PasswordRecoveryFinishModal({
  accessToken,
  onClose,
  onSuccess,
}: {
  accessToken: string
  onClose: () => void
  onSuccess: (message: string) => void
}) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const passwordProblem = validatePassword(newPassword)
    if (passwordProblem) { setError(passwordProblem); return }
    if (newPassword !== confirmPassword) { setError('As senhas não coincidem.'); return }

    setLoading(true)
    try {
      const message = await authApi.completePasswordRecovery(accessToken, newPassword, confirmPassword)
      onSuccess(message)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Não foi possível redefinir a senha. Solicite outro link.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Definir nova senha" width={420}>
      <form onSubmit={handleSubmit} className="csp-login-29">
        <div role="status" className="csp-login-banner csp-login-banner-spaced">
          Atenção: você está trocando a senha da conta vinculada ao e-mail de recuperação.
          Confirme somente se foi você quem solicitou esta alteração.
        </div>
        {error && <div role="alert" className="csp-login-banner csp-login-banner-error">{error}</div>}
        <TextInput
          label="Nova senha"
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          required autoComplete="new-password"
        />
        <TextInput
          label="Repetir nova senha"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          required autoComplete="new-password"
        />
        <div className="csp-login-30">
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={loading || !newPassword || !confirmPassword}>
            {loading ? 'Confirmando...' : 'Confirmar nova senha'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ── Modal "criar conta" ─────────────────────────────────────────────────────────

interface RegisterModalProps {
  enabled: boolean
  onClose: () => void
}

function RegisterModal({ enabled, onClose }: RegisterModalProps) {
  const [fullName, setFullName] = useState('')
  const [cpf, setCpf] = useState('')
  const [email, setEmail] = useState('')
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
    if (fullName.trim().split(/\s+/).length < 2) { setError('Informe nome e sobrenome.'); return }
    if (!validCpf(cpf)) { setError('Informe um CPF válido.'); return }
    const passwordProblem = validatePassword(password)
    if (passwordProblem) { setError(passwordProblem); return }
    if (password !== confirmPassword) {
      setError('As senhas não coincidem')
      return
    }

    setLoading(true)
    try {
      const result = await authApi.register(fullName, cpf, email, password, confirmPassword)
      setSuccess(result.msg || 'Enviamos uma confirmação ao seu e-mail. Confirme antes de entrar.')
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
        {!enabled && <p className="csp-login-banner csp-login-banner-error">Cadastro aguardando configuração do Supabase Auth.</p>}
        {error && <div className="csp-login-banner csp-login-banner-error">{error}</div>}
        {success && <div className="csp-login-banner csp-login-banner-success">{success}</div>}

        <TextInput
          label="Nome completo *"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          autoComplete="name"
          disabled={!!success}
        />
        <TextInput label="CPF *" value={cpf} onChange={e => setCpf(e.target.value)} required
          inputMode="numeric" maxLength={18} autoComplete="off" placeholder="000.000.000-00" disabled={!!success} />
        <TextInput
          label="E-mail"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
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
          <label><input type="checkbox" checked={acceptedTerms} onChange={e=>setAcceptedTerms(e.target.checked)} required /> Aceito os <a href="/termos" target="_blank" rel="noreferrer">Termos de Uso</a> e li a <a href="/privacidade" target="_blank" rel="noreferrer">Política de Privacidade</a> e a <a href="/dados-coletados" target="_blank" rel="noreferrer">lista de dados tratados</a>. (Obrigatório)</label>
          <p className="csp-login-33">No primeiro acesso, você poderá escolher se compartilha <strong>uma única localização aproximada</strong> para análise comercial. O navegador pedirá permissão separadamente. Você poderá recusar sem limitar sua conta e excluir o ponto em Configurações.</p>
        </div>
        <div className="csp-login-34">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !!success || !acceptedTerms || !enabled}>
            {loading ? 'Enviando...' : 'Criar conta'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}


function GoogleSetupModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => Promise<void> }) {
  const [fullName, setFullName] = useState('')
  const [cpf, setCpf] = useState('')
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!acceptedTerms) { setError('Aceite os Termos de Uso para continuar.'); return }
    if (fullName.trim().split(/\s+/).length < 2 || !validCpf(cpf)) { setError('Informe nome completo e CPF válido.'); return }
    setLoading(true)
    setError('')
    try {
      await authApi.completeGoogle(fullName, cpf)
      await onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível concluir o cadastro Google.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Concluir cadastro com Google" width={400}>
      <form onSubmit={submit} className="csp-login-31">
        <p>Confirme seus dados cadastrais. O Google gerencia sua senha de acesso.</p>
        {error && <div className="csp-login-banner csp-login-banner-error">{error}</div>}
        <TextInput label="Nome completo *" value={fullName} onChange={e => setFullName(e.target.value)}
          required minLength={5} maxLength={150} autoComplete="name" />
        <TextInput label="CPF *" value={cpf} onChange={e => setCpf(e.target.value)}
          required inputMode="numeric" maxLength={18} autoComplete="off" />
        <label><input type="checkbox" checked={acceptedTerms}
          onChange={e => setAcceptedTerms(e.target.checked)} required /> Aceito os{' '}
          <a href="/termos" target="_blank" rel="noreferrer">Termos de Uso</a> e li a{' '}
          <a href="/privacidade" target="_blank" rel="noreferrer">Política de Privacidade</a>.</label>
        <div className="csp-login-34">
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="primary" disabled={!acceptedTerms || loading}>
            {loading ? 'Concluindo...' : 'Criar conta'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
