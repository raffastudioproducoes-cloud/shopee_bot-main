import { BillingAdminPanel } from "../components/plans/BillingAdminPanel"
import { Panel } from "../components/ui/Panel"

// Cobrança fica em área própria do ADMIN, separada de "Diagnóstico" (redes e plataformas).
export default function AdminBillingPage() {
  return (
    <div className="admin-diagnostic-page">
      <h1>Cobrança</h1>
      <p>Pagamentos e assinaturas dos planos Pro e Premium pelo Asaas. Chave e token ficam no servidor e nunca aparecem aqui.</p>
      <Panel surface="dark" padding={18}><BillingAdminPanel /></Panel>
    </div>
  )
}
