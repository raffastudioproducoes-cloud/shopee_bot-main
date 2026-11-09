import './LegalLayout.css'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/authStore'
import { isAdminVisitingSite } from '../../lib/adminSiteFlag'

// Mesmo breakpoint usado em LoginPage.tsx (768px) — não existe um padrão
// central de breakpoints no projeto, então cada componente com CSS próprio
// declara o seu.

interface LegalLayoutProps {
  title: string
  updatedAt: string
  children: ReactNode
}

/** Layout compartilhado pelas páginas legais públicas.
 * O retorno consulta a sessão real, pois o estado persistido no navegador pode estar desatualizado. */
export function LegalLayout({ title, updatedAt, children }: LegalLayoutProps) {
  const navigate = useNavigate()
  const [returning, setReturning] = useState(false)

  const handleReturn = async () => {
    if (returning) return
    setReturning(true)
    try {
      const user = await authApi.me()
      const auth = useAuthStore.getState()
      if (!auth.isAuthenticated) auth.login(user)
      else auth.setUser(user)
      const home = user.access === 'ADMIN' && !isAdminVisitingSite() ? '/admin/overview' : '/'
      await navigate({ to: home })
    } catch {
      // Não confiar apenas no estado local caso o cookie tenha expirado.
      useAuthStore.getState().logout()
      await navigate({ to: '/login' })
    } finally {
      setReturning(false)
    }
  }
  useEffect(() => {
    const previous = document.title
    document.title = `${title} · Auto Orbital`
    return () => {
      document.title = previous
    }
  }, [title])

  return (
    <div className="legal-page">
      
      <header className="legal-page__header">
        <button
          type="button"
          onClick={() => { void handleReturn() }}
          disabled={returning}
          className="legal-page__back"
        >
          {returning ? 'Voltando...' : '← Voltar'}
        </button>
        <span className="legal-page__separator">·</span>
        <span className="legal-page__brand">
          Auto Orbital
        </span>
      </header>

      <main className="legal-page__body">
        <h1 className="legal-page__title">
          {title}
        </h1>
        <p className="legal-page__updated">
          Última atualização: {updatedAt}
        </p>

        {children}
      </main>
    </div>
  )
}
