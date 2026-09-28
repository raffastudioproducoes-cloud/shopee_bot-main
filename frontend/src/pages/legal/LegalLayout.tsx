import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Link } from '@tanstack/react-router'

// Mesmo breakpoint usado em LoginPage.tsx (768px) — não existe um padrão
// central de breakpoints no projeto, então cada componente com CSS próprio
// declara o seu.
const legalPageStyles = `
  .legal-page { min-height: 100vh; background: var(--bg-app); }
  .legal-page__header {
    position: sticky; top: 0; z-index: 1;
    display: flex; align-items: center; gap: var(--sp-6);
    padding: var(--sp-6) var(--sp-6);
    background: var(--bg-app);
    border-bottom: 1px solid var(--border-hairline);
  }
  .legal-page__body {
    max-width: 760px; margin: 0 auto;
    padding: var(--sp-10) var(--sp-6) var(--sp-12);
  }
  .legal-page__body h2 {
    font: var(--fw-semibold) var(--fs-subtitle)/var(--lh-snug) var(--font-display);
    color: var(--text-display);
    margin: var(--sp-10) 0 var(--sp-4);
  }
  .legal-page__body h2:first-of-type { margin-top: var(--sp-6); }
  .legal-page__body p, .legal-page__body li {
    font: var(--text-role-body);
    color: var(--text-body);
  }
  .legal-page__body p { margin: 0 0 var(--sp-5); }
  .legal-page__body ul { margin: 0 0 var(--sp-5); padding-left: var(--sp-7); }
  .legal-page__body li { margin-bottom: var(--sp-2); }
  .legal-page__body strong { color: var(--text-display); font-weight: var(--fw-semibold); }
  .legal-placeholder {
    color: var(--amber-300);
    background: rgba(243, 201, 125, 0.12);
    border-radius: var(--r-xs);
    padding: 1px 6px;
    font-weight: var(--fw-medium);
  }
  @media (min-width: 768px) {
    .legal-page__header { padding: var(--sp-7) var(--sp-9); }
    .legal-page__body { padding: var(--sp-12) var(--sp-9) var(--sp-12); }
  }
`

interface LegalLayoutProps {
  title: string
  updatedAt: string
  children: ReactNode
}

/** Casca compartilhada das páginas públicas /termos e /privacidade: mesmo
 * header com volta pro login, mesma tipografia de prosa. Extraído porque as
 * duas páginas são idênticas nisso — só o conteúdo das seções muda. */
export function LegalLayout({ title, updatedAt, children }: LegalLayoutProps) {
  useEffect(() => {
    const previous = document.title
    document.title = `${title} · Shopee Auto Vendas`
    return () => {
      document.title = previous
    }
  }, [title])

  return (
    <div className="legal-page">
      <style>{legalPageStyles}</style>

      <header className="legal-page__header">
        <Link
          to="/login"
          style={{
            color: 'var(--text-muted)',
            font: 'var(--text-role-body)',
            textDecoration: 'none',
          }}
        >
          ← Voltar
        </Link>
        <span style={{ color: 'var(--text-muted)' }}>·</span>
        <span style={{ font: 'var(--fw-semibold) var(--fs-body)/1 var(--font-display)', color: 'var(--text-display)' }}>
          Shopee Auto Vendas
        </span>
      </header>

      <main className="legal-page__body">
        <h1 style={{ font: 'var(--text-role-hero)', color: 'var(--text-display)', margin: '0 0 8px', fontSize: 'var(--fs-amount)' }}>
          {title}
        </h1>
        <p style={{ color: 'var(--text-muted)', font: 'var(--text-role-label)', marginBottom: 'var(--sp-9)' }}>
          Última atualização: {updatedAt}
        </p>

        {children}
      </main>
    </div>
  )
}
