import type { PlanUsage } from "../../api/planUsage"
import "./productQuotaBar.css"

type Props = {
  plan?: PlanUsage
  loading: boolean
  error: boolean
  onUpgrade: () => void
}

export function ProductQuotaBar({ plan, loading, error, onUpgrade }: Props) {
  const usage = plan?.resources.products
  const used = usage?.usage_status === "available" && typeof usage.used === "number"
    ? usage.used.toLocaleString("pt-BR") : null
  const unlimited = !!plan?.is_admin || !!usage?.unlimited
  const quota = loading ? "Consultando cota..."
    : error || !plan || !usage ? "Cota indisponível"
    : unlimited ? `${used ?? "Uso indisponível"} cadastrados · sem cota comercial`
    : used !== null && typeof usage.limit === "number"
      ? `${used} de ${usage.limit.toLocaleString("pt-BR")} utilizados`
      : "Cota indisponível"
  const canUpgrade = !!plan && !plan.is_admin && plan.plan_tier !== "premium"

  return (
    <section className="product-quota-bar" aria-label="Cota de produtos da conta">
      <div className="product-quota-bar__summary">
        <strong>Cota de produtos</strong>
        <span aria-live="polite">{quota}</span>
      </div>
      {canUpgrade ? (
        <button className="product-quota-bar__upgrade" type="button" onClick={onUpgrade}>
          Melhorar plano
        </button>
      ) : null}
    </section>
  )
}
