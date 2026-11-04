import { useState } from "react"
import { RegionConsent } from "../components/profiles/RegionConsent"
import { AcquisitionConsent } from "../components/profiles/AcquisitionConsent"
import { BackupSection } from "../components/profiles/BackupSection"
import { Panel } from "../components/ui/Panel"
import { PlanComparison } from "../components/plans/PlanComparison"
import { Button } from "../components/ui/Button"
import { PasswordRecoveryRequestModal } from "../components/auth/PasswordRecoveryRequestModal"

export function SettingsPage() {
  const [recoveryOpen, setRecoveryOpen] = useState(false)

  return (
    <div className="csp-s-0379">
      <div>
        <h1 className="csp-s-0380">Configurações</h1>
        <p className="csp-s-0381">Ajustes da sua conta.</p>
      </div>
      <PlanComparison />
      <Panel className="settings-password-card" padding={24} style={{ maxWidth: 420 }}>
        <div className="csp-s-0382">
          <h2 className="csp-s-0383">Trocar senha</h2>
          <p>Por segurança, sua senha é gerenciada pelo Supabase.
            Vamos enviar um link para o e-mail da conta. A nova senha só poderá
            ser definida após abrir esse link.</p>
          <Button type="button" onClick={() => setRecoveryOpen(true)}>
            Solicitar link por e-mail
          </Button>
        </div>
      </Panel>
      <section aria-labelledby="privacy-settings-title" className="csp-s-0387">
        <div>
          <h2 id="privacy-settings-title" className="csp-s-0388">Privacidade, localização e origem</h2>
          <p className="csp-s-0389">Controle seus dados opcionais e autorizações.</p>
        </div>
        <RegionConsent />
        <AcquisitionConsent />
      </section>
      <BackupSection />
      {recoveryOpen && (
        <PasswordRecoveryRequestModal onClose={() => setRecoveryOpen(false)} />
      )}
    </div>
  )
}
