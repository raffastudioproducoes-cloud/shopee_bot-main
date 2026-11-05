import type { PlanUsage } from "../../api/planUsage"
import "./productQuotaBar.css"

type Props = {
  plan?: PlanUsage
  resource?: "products" | "lists"
  loading: boolean
  error: boolean
  onUpgrade: () => void
}

export function ResourceQuotaBar({ plan, resource = "products", loading, error, onUpgrade }: Props) {
  const usage = plan?.resources[resource]
  const isLists = resource === "lists"
  const plural = isLists ? "cadastradas" : "cadastrados"
  const usedWord = isLists ? "utilizadas" : "utilizados"
  const used = usage?.usage_status === "available" && typeof usage.used === "number"
    ? usage.used.toLocaleString("pt-BR") : null
  const unlimited = !!plan?.is_admin || !!usage?.unlimited
  const quota = loading ? "Consultando cota..."
    : error || !plan || !usage ? "Cota indisponível"
    : unlimited ? `${used ?? "Uso indisponível"} ${plural} · sem cota comercial`
    : used !== null && typeof usage.limit === "number"
      ? `${used} de ${usage.limit.toLocaleString("pt-BR")} ${usedWord}`
      : "Cota indisponível"
  const canUpgrade = !!plan && !plan.is_admin && plan.plan_tier !== "premium"

  return (
    <section className="product-quota-bar" aria-label={isLists ? "Cota de listas do perfil" : "Cota de produtos da conta"}>
      <div className="product-quota-bar__summary">
        <strong>{isLists ? "Cota de listas" : "Cota de produtos"}</strong>
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

// Mantém compatibilidade com a página e os testes existentes de Produtos.
export const ProductQuotaBar = ResourceQuotaBar
