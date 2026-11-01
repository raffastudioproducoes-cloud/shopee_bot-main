import '../../pages/LoginPage.css'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { authApi } from '../../api/auth'
import { Button } from '../ui/Button'
import { TextInput } from '../ui/TextInput'
import { Modal } from '../ui/Modal'

interface PasswordRecoveryRequestModalProps {
  initialEmail?: string
  onClose: () => void
}

/** Solicita o link ao Supabase Auth. Nenhuma senha é alterada neste formulário. */
export function PasswordRecoveryRequestModal({ initialEmail = '', onClose }: PasswordRecoveryRequestModalProps) {
  const [email, setEmail] = useState(initialEmail.includes('@') ? initialEmail : '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const message = await authApi.requestPasswordRecovery(email.trim())
      setSuccess(message)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Não foi possível solicitar o link. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Recuperar senha por e-mail" width={420}>
      <form onSubmit={handleSubmit} className="csp-login-29">
        <p>Digite o e-mail cadastrado. Se houver uma conta, o Supabase enviará um link seguro.
          Abra o link recebido para definir sua nova senha.</p>
        {error && <div role="alert" className="csp-login-banner csp-login-banner-error">{error}</div>}
        {success && <div role="status" className="csp-login-banner csp-login-banner-success">{success}</div>}
        <TextInput label="E-mail da conta" type="email" value={email}
          onChange={(event) => setEmail(event.target.value)} autoComplete="email"
          placeholder="seu@email.com" required disabled={!!success} />
        <div className="csp-login-30">
          <Button type="button" variant="ghost" onClick={onClose}>
            {success ? 'Fechar' : 'Cancelar'}
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !!success || !email.trim()}>
            {loading ? 'Solicitando...' : 'Enviar link para o e-mail'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
