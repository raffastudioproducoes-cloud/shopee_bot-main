import type { PlanUsage, ResourceUsage } from "../api/planUsage"

export type QuotaScope = "products" | "lists" | "profiles" | "publishing" | "campaigns"

/** Apenas apresentação: a API continua responsável pelos limites e permissões. */
export function canOfferPlanUpgrade(plan: Pick<PlanUsage, "is_admin" | "plan_tier"> | undefined): boolean {
  return !!plan && !plan.is_admin && plan.plan_tier !== "premium"
}

function knownLimit(label: string, usage: ResourceUsage | undefined, period: string): string | null {
  if (!usage) return null
  if (usage.unlimited) return `${label}: sem cota comercial`
  if (usage.limit === null) return null
  const used = usage.usage_status === "available" && usage.used !== null
    ? `${usage.used.toLocaleString("pt-BR")} / ` : ""
  return `${label}: ${used}${usage.limit.toLocaleString("pt-BR")}${period}`
}

export function quotaBarText(plan: PlanUsage | undefined, scope: QuotaScope, loading: boolean, error: boolean) {
  const title = ({
    products: "Cota de produtos", lists: "Cota de listas", profiles: "Cota de perfis",
    publishing: "Cota de publicações", campaigns: "Cota de campanhas",
  })[scope]
  if (loading) return { title, detail: "Consultando cota..." }
  if (error || !plan) return { title, detail: "Cota indisponível" }

  if (scope === "publishing") {
    const limits = [
      knownLimit("Enviar agora", plan.resources.immediate, "/hora"),
      knownLimit("Recorrências", plan.resources.recurring, "/dia"),
    ].filter(Boolean)
    return { title, detail: limits.join(" · ") || (plan.is_admin ? "Sem cota comercial" : "Limites não informados") }
  }

  if (scope === "campaigns") {
    if (!plan.campaigns_enabled && !plan.is_admin) return { title, detail: "Campanhas não incluídas neste plano" }
    const count = typeof plan.active_campaigns_count === "number"
      ? plan.active_campaigns_count.toLocaleString("pt-BR") : null
    const active = plan.is_admin || plan.active_campaigns_limit === null
      ? `${count === null ? "" : count + " ativas · "}sem cota comercial`
      : `${count === null ? "" : count + " / "}${plan.active_campaigns_limit.toLocaleString("pt-BR")} ativas`
    const duration = plan.campaign_days > 0 ? ` · Até ${plan.campaign_days} dias` : ""
    const frequency = plan.campaign_posts_per_day !== null
      ? ` · ${plan.campaign_posts_per_day} posts/dia` : ""
    return { title, detail: `${active}${duration}${frequency}` }
  }

  const usage = plan.resources[scope]
  const isLists = scope === "lists"
  const plural = isLists ? "cadastradas" : "cadastrados"
  const usedWord = isLists ? "utilizadas" : "utilizados"
  const used = usage?.usage_status === "available" && typeof usage.used === "number"
    ? usage.used.toLocaleString("pt-BR") : null
  const unlimited = !!plan.is_admin || !!usage?.unlimited
  const detail = !usage ? "Cota indisponível"
    : unlimited ? `${used ?? "Uso indisponível"} ${plural} · sem cota comercial`
    : used !== null && typeof usage.limit === "number"
      ? `${used} de ${usage.limit.toLocaleString("pt-BR")} ${usedWord}`
      : "Cota indisponível"
  return { title, detail }
}
