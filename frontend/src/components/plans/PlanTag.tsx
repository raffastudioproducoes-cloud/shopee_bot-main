import type { ReactNode } from "react"
import "./planTag.css"

export type PlanTier = "admin" | "premium" | "pro" | "free"

/** Etiqueta do plano. Admin: rubi/carmesim com brilho; Premium: paleta da marca com brilho;
 *  Pro: azul da marca; Free: neutra e simples (a diferença visual é parte do apelo do upgrade). */
export function PlanTag({ tier, children }: { tier: PlanTier; children: ReactNode }) {
  return <span className={`plan-tag plan-tag--${tier}`}>{children}</span>
}

export function planTierOf(plan: { is_admin?: boolean; plan_tier?: string } | undefined): PlanTier {
  if (plan?.is_admin) return "admin"
  if (plan?.plan_tier === "premium") return "premium"
  if (plan?.plan_tier === "pro" || plan?.plan_tier === "plus") return "pro"
  return "free"
}
