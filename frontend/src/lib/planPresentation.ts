import type { PlanUsage, ResourceUsage } from "../api/planUsage"

/** Somente apresentação: nunca autoriza uma operação do servidor. */
export function accountPlanLabel(plan: Pick<PlanUsage, "is_admin" | "plan_tier"> | undefined): string {
  if (!plan) return "Plano indisponível"
  if (plan.is_admin) return "Administrador"
  return ({ free: "Free", pro: "Pro", plus: "Pro", premium: "Premium" })[plan.plan_tier] ?? "Plano indisponível"
}
export function usageLabel(resource: ResourceUsage | undefined): string {
  if (!resource) return "Uso e limite indisponíveis"
  const used = resource.usage_status === "available" && resource.used !== null
    ? resource.used.toLocaleString("pt-BR") : "Uso indisponível"
  const limit = resource.unlimited ? "sem cota comercial"
    : resource.limit === null ? "limite indisponível" : resource.limit.toLocaleString("pt-BR")
  return `${used} / ${limit}`
}
export function resourceAtLimit(resource: ResourceUsage | undefined): boolean {
  return !!resource && !resource.unlimited && resource.usage_status === "available"
    && resource.used !== null && resource.limit !== null && resource.used >= resource.limit
}
export function campaignUiCaps(plan: PlanUsage | undefined) {
  return {
    days: plan ? Math.min(30, plan.campaign_days) : 0,
    posts: plan ? Math.min(15, plan.campaign_posts_per_day ?? (plan.is_admin ? 15 : 0)) : 0,
  }
}
