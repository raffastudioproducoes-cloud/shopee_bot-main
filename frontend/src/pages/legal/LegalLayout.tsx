import './LegalLayout.css'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { useSiteLang, type SiteLang } from '../../lib/siteLang'
import { legalLinks } from '../presentation/AppInfoSection'

// Mesmo breakpoint usado em LoginPage.tsx (768px) — não existe um padrão
// central de breakpoints no projeto, então cada componente com CSS próprio
// declara o seu.

interface LegalLayoutProps {
  title: Record<SiteLang, string>
  updatedAt: Record<SiteLang, string>
  children: (lang: SiteLang) => ReactNode
}

/** Layout das páginas legais públicas, em português e inglês.
 * "Voltar" leva à página inicial: ela mesma confere a sessão no backend e manda quem está logado para /app. */
export function LegalLayout({ title, updatedAt, children }: LegalLayoutProps) {
  const [lang, setLang] = useSiteLang()

  useEffect(() => {
    const previous = document.title
    document.title = `${title[lang]} · Auto Orbital`
    return () => {
      document.title = previous
    }
  }, [title, lang])

  return (
    <div className="legal-page">
      <header className="legal-page__header">
        <a href="/" className="legal-page__back">
          {lang === 'en' ? '← Home' : '← Início'}
        </a>
        <span className="legal-page__separator">·</span>
        <span className="legal-page__brand">Auto Orbital</span>
        <div role="group" aria-label="Idioma / Language" className="legal-page__lang">
          <button type="button" onClick={() => setLang('pt')} aria-pressed={lang === 'pt'}>PT</button>
          <button type="button" onClick={() => setLang('en')} aria-pressed={lang === 'en'}>EN</button>
        </div>
      </header>

      <main className="legal-page__body" lang={lang === 'en' ? 'en' : 'pt-BR'}>
        <h1 className="legal-page__title">{title[lang]}</h1>
        <p className="legal-page__updated">
          {lang === 'en' ? 'Last updated' : 'Última atualização'}: {updatedAt[lang]}
        </p>

        {children(lang)}
      </main>

      <footer className="legal-page__footer">
        <nav aria-label={lang === 'en' ? 'Legal documents' : 'Documentos legais'}>
          {legalLinks(lang).map((l) => <a key={l.href} href={l.href}>{l.label}</a>)}
        </nav>
        <p>© 2026 Raffa Studio Produções · Auto Orbital</p>
      </footer>
    </div>
  )
}
