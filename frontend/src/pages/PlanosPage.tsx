import { useSearch } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { billingApi } from "../api/billing"
import { PlanCheckout } from "../components/plans/PlanCheckout"
import { SubscriptionCard } from "../components/plans/SubscriptionCard"
import { PlanComparison } from "../components/plans/PlanComparison"
import { SandboxGuide } from "../components/plans/SandboxGuide"
import { usePlanUsage } from "../hooks/usePlanUsage"
import { parsePlanosSearch } from "../lib/planIntent"
import "../components/plans/planCheckout.css"

const RETURN_MESSAGES = {
  sucesso: "Pagamento enviado. O plano é liberado assim que o Asaas confirmar (pode levar alguns minutos).",
  cancelada: "Contratação cancelada. Nenhuma cobrança foi feita.",
  expirada: "O link de pagamento expirou. Escolha o plano de novo para gerar outro.",
} as const

const FROM_TEXT: Record<string, string> = {
  produtos: "Mais produtos no catálogo", listas: "Mais listas por perfil", perfis: "Mais perfis na conta",
  publicacao: "Mais publicações por hora e por dia", campanhas: "Campanhas e mais envios", automacao: "Automação de posts",
}

export default function PlanosPage() {
  const search = parsePlanosSearch(useSearch({ strict: false }) as Record<string, unknown>)
  const usage = usePlanUsage()
  const sub = useQuery({ queryKey: ["billing-subscription"], queryFn: billingApi.subscription, retry: false })
  const prices = useQuery({ queryKey: ["billing-plans"], queryFn: billingApi.plans, staleTime: 5 * 60_000 })
  const plan = usage.data
  const tier = plan?.plan_tier === "plus" ? "pro" : plan?.plan_tier
  const hasSubscription = ["pending", "active", "overdue"].includes(sub.data?.subscription?.status ?? "")

  return (
    <div className="planos-page">
      <header>
        <h1>Planos e pagamento</h1>
        <p>{search.de && FROM_TEXT[search.de] ? `${FROM_TEXT[search.de]}: escolha o plano que libera.` : "Escolha o plano, o período e a forma de pagamento."}</p>
      </header>
      {search.assinatura && (
        <p className={`plan-checkout__notice plan-checkout__notice--${search.assinatura}`} role="status">
          {RETURN_MESSAGES[search.assinatura]}
        </p>
      )}
      {prices.data?.sandbox && prices.data.checkout_enabled && <SandboxGuide />}
      <SubscriptionCard tier={tier} />
      {plan?.is_admin
        ? <p className="plan-checkout__note" role="status">Contas administradoras não têm cota comercial e não precisam de plano.</p>
        : <PlanCheckout initialTier={search.plano} initialPeriod={search.periodo} currentTier={tier} hasSubscription={hasSubscription} />}
      <PlanComparison />
    </div>
  )
}
