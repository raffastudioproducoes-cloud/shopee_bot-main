import { usePlanUsage } from "../../hooks/usePlanUsage"
import { accountPlanLabel } from "../../lib/planPresentation"
import "./planComparison.css"

const plans = [
  { key: "Free", products: "100", profiles: "1", lists: "20 por perfil", immediate: "1 por hora", recurring: "1 por dia", campaigns: "Não incluídas" },
  { key: "Pro", products: "500", profiles: "3", lists: "20 por perfil", immediate: "3 por hora", recurring: "5 por dia", campaigns: "Até 2 por perfil*" },
  { key: "Premium", products: "2.000", profiles: "5", lists: "100 por perfil", immediate: "5 por hora", recurring: "5 por dia", campaigns: "Até 5 por perfil*" },
] as const

const rows = [
  { name: "Produtos da conta", field: "products" },
  { name: "Perfis por conta", field: "profiles" },
  { name: "Listas de produtos", field: "lists" },
  { name: "Publicações imediatas", field: "immediate" },
  { name: "Publicações recorrentes", field: "recurring" },
  { name: "Campanhas", field: "campaigns" },
] as const

export function PlanComparison() {
  const { data } = usePlanUsage()
  const currentPlan = accountPlanLabel(data)

  return (
    <section id="planos" className="plan-comparison" aria-labelledby="plan-comparison-title">
      <div className="plan-comparison__header">
        <div>
          <h2 id="plan-comparison-title">Planos e limites</h2>
          <p>Compare as cotas da conta e as opções para suas necessidades.</p>
        </div>
        <span className="plan-comparison__current">Plano atual: {currentPlan}</span>
      </div>
      <div className="plan-comparison__scroll" tabIndex={0} aria-label="Comparação dos planos">
        <table>
          <thead>
            <tr>
              <th scope="col">Recurso</th>
              {plans.map((plan) => (
                <th key={plan.key} scope="col" className={plan.key === "Pro" ? "plan-comparison__rec" : undefined}>
                  {plan.key}
                  {plan.key === "Pro" ? <span className="plan-comparison__badge">Recomendado</span> : null}
                  {plan.key === currentPlan ? <span className="plan-comparison__you">Seu plano</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.field}>
                <th scope="row">{row.name}</th>
                {plans.map((plan) => <td key={plan.key} className={plan.key === "Pro" ? "plan-comparison__rec" : undefined}>{plan[row.field]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="plan-comparison__note">
        *Campanhas sujeitas aos limites de duração, ritmo e disponibilidade do serviço.
        Regras de segurança e das redes sociais continuam válidas para todos os planos.
      </p>
      <p className="plan-comparison__note">
        A contratação e a mudança de plano ainda não estão disponíveis neste painel.
        O plano Administrador não possui cota comercial, mas segue os limites operacionais.
      </p>
    </section>
  )
}
