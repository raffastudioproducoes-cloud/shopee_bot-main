import type { PlanUsage } from "../../api/planUsage"
import { canOfferPlanUpgrade, quotaBarText, type QuotaScope } from "../../lib/quotaBarPresentation"
import "./productQuotaBar.css"

type Props = {
  plan?: PlanUsage
  resource?: QuotaScope
  loading: boolean
  error: boolean
  onUpgrade: () => void
}

export function ResourceQuotaBar({ plan, resource = "products", loading, error, onUpgrade }: Props) {
  const { title, detail } = quotaBarText(plan, resource, loading, error)
  const canUpgrade = canOfferPlanUpgrade(plan)

  return (
    <section className="product-quota-bar" aria-label={title}>
      <div className="product-quota-bar__summary">
        <strong>{title}</strong>
        <span aria-live="polite">{detail}</span>
      </div>
      {canUpgrade ? (
        <button className="product-quota-bar__upgrade" type="button" onClick={onUpgrade}>
          Melhorar plano
        </button>
      ) : null}
    </section>
  )
}

// Mantém compatibilidade com a página e os testes existentes de Produtos.
export const ProductQuotaBar = ResourceQuotaBar

