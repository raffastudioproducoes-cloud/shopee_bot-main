import './AppFooter.css'
import { Link } from '@tanstack/react-router'
import { APP_VERSION } from '../../appMeta'
import { Icon } from '../ui/Icon'

type AppFooterProps = {
  variant: 'login' | 'app'
}


export function AppFooter({ variant }: AppFooterProps) {
  const loginFooter = variant === 'login'

  return (
    <footer className={`app-footer app-footer--${variant}`}>
      
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
