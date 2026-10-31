import { Link } from '@tanstack/react-router'
import { APP_VERSION } from '../../appMeta'
import { Icon } from '../ui/Icon'

type AppFooterProps = {
  variant: 'login' | 'app'
}

const footerStyles = `
  .app-footer {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 20px 32px;
    width: 100%;
    border-top: 1px solid var(--border-hairline);
    color: var(--text-muted);
  }
  .app-footer--login {
    padding: 18px clamp(20px, 3vw, 52px) calc(18px + env(safe-area-inset-bottom));
    background: rgba(8, 12, 22, 0.92);
  }
  .app-footer--app {
    margin-top: auto;
    padding: 18px 0 calc(4px + env(safe-area-inset-bottom));
  }
  .app-footer__identity { min-width: 0; }
  .app-footer__company {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 4px;
    color: var(--text-body);
    font: var(--fw-semibold) var(--fs-caption)/1.35 var(--font-sans);
  }
  .app-footer__copyright { margin: 0; font: var(--text-role-caption); }
  .app-footer__version {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--border-hairline);
    border-radius: var(--r-xs);
    padding: 2px 7px;
    color: var(--text-display);
    background: var(--surface-inset);
    font: var(--fw-semibold) var(--fs-caption)/1 var(--font-mono);
    white-space: nowrap;
  }
  .app-footer__links {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 8px 18px;
  }
  .app-footer__link, .app-footer__security {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-muted);
    font: var(--text-role-caption);
    text-decoration: none;
  }
  .app-footer__link:hover { color: var(--text-display); }
  .app-footer__link:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: var(--r-xs); }
  .app-footer__security { color: var(--text-body); }
  @media (max-width: 900px) {
    .app-footer { grid-template-columns: 1fr; gap: 14px; }
    .app-footer__links { justify-content: flex-start; }
  }
`

export function AppFooter({ variant }: AppFooterProps) {
  const loginFooter = variant === 'login'

  return (
    <footer className={`app-footer app-footer--${variant}`}>
      <style>{footerStyles}</style>

      <div className="app-footer__identity">
        <p className="app-footer__company">
          <span>© 2026 Raffa Studio Produções</span>
          <span aria-hidden="true">·</span>
          <span>Empresa registrada desde 2026</span>
          <span className="app-footer__version">v{APP_VERSION}</span>
        </p>
        <p className="app-footer__copyright">
          Todos os direitos reservados · Suporte técnico: contato.raffasp@gmail.com
        </p>
      </div>

      <nav className="app-footer__links" aria-label="Links institucionais">
        <span className="app-footer__security">
          <Icon name="shield-check" size={15} /> Dados protegidos
        </span>
        {loginFooter ? (
          <a className="app-footer__link" href="mailto:contato.raffasp@gmail.com?subject=Ajuda%20-%20Shopee%20Auto%20Vendas">
            <Icon name="help-circle" size={15} /> Ajuda & FAQ
          </a>
        ) : (
          <Link className="app-footer__link" to="/ajuda">
            <Icon name="help-circle" size={15} /> Ajuda & FAQ
          </Link>
        )}
        <Link className="app-footer__link" to="/privacidade">
          <Icon name="lock" size={15} /> Privacidade & LGPD
        </Link>
        <Link className="app-footer__link" to="/dados-coletados">Dados coletados</Link>
        <Link className="app-footer__link" to="/termos">
          <Icon name="file-text" size={15} /> Termos de Uso
        </Link>
      </nav>
    </footer>
  )
}
