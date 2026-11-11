import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { billingApi, type BillingPeriod, type BillingType, type PaidTier, type PlanPrice } from "../../api/billing"
import { ApiError } from "../../lib/api"
import { Button } from "../ui/Button"
import { PlanTag } from "./PlanTag"
import "./planCheckout.css"

export const PERIODS: { id: BillingPeriod; label: string }[] = [
  { id: "monthly", label: "Mensal" },
  { id: "quarterly", label: "3 meses" },
  { id: "semiannual", label: "6 meses" },
  { id: "yearly", label: "1 ano" },
]
const TIERS: { id: PaidTier; label: string }[] = [{ id: "pro", label: "Pro" }, { id: "premium", label: "Premium" }]
const METHODS: { id: BillingType; label: string; hint: string }[] = [
  { id: "CREDIT_CARD", label: "Cartão de crédito", hint: "Renova sozinho no cartão a cada ciclo." },
  { id: "PIX", label: "Pix", hint: "A cada ciclo chega uma fatura Pix para pagar." },
]
const RETURN_MESSAGES: Record<string, string> = {
  sucesso: "Pagamento enviado. O plano é ativado assim que o Asaas confirmar (pode levar alguns minutos).",
  cancelada: "Contratação cancelada. Nenhuma cobrança foi feita.",
  expirada: "O link de pagamento expirou. Gere um novo quando quiser.",
}

export const brl = (cents: number) =>
  (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })

export function discountLabel(bps: number) {
  return bps ? `−${(bps / 100).toLocaleString("pt-BR")}%` : ""
}

export function priceFor(prices: PlanPrice[] | undefined, tier: PaidTier, period: BillingPeriod) {
  return prices?.find((p) => p.tier === tier && p.period === period)
}

function returnStatus(): string | null {
  if (typeof window === "undefined") return null
  const value = new URLSearchParams(window.location.search).get("assinatura")
  return value && value in RETURN_MESSAGES ? value : null
}

export function PlanCheckout({ currentTier }: { currentTier?: string }) {
  const [period, setPeriod] = useState<BillingPeriod>("yearly")
  const [method, setMethod] = useState<BillingType>("CREDIT_CARD")
  const [status] = useState(returnStatus)
  const prices = useQuery({ queryKey: ["billing-plans"], queryFn: billingApi.plans, staleTime: 5 * 60_000 })
  const checkout = useMutation({
    mutationFn: (tier: PaidTier) => billingApi.checkout({ tier, period, billing_type: method }),
    onSuccess: (data) => { window.location.assign(data.checkout_url) },
  })
  const error = checkout.error instanceof ApiError ? checkout.error : null
  const needsProfile = error?.status === 422 && error.message.startsWith("Complete os dados")

  return (
    <div className="plan-checkout" aria-labelledby="plan-checkout-title">
      <h3 id="plan-checkout-title">Assinar um plano</h3>
      {status && <p className={`plan-checkout__notice plan-checkout__notice--${status}`} role="status">{RETURN_MESSAGES[status]}</p>}

      <div className="plan-checkout__periods" role="radiogroup" aria-label="Período de contratação">
        {PERIODS.map((p) => {
          const bps = priceFor(prices.data?.prices, "pro", p.id)?.discount_bps ?? 0
          return (
            <button key={p.id} type="button" role="radio" aria-checked={period === p.id}
              className="plan-checkout__period" onClick={() => setPeriod(p.id)}>
              {p.label}{bps ? <span className="plan-checkout__off">{discountLabel(bps)}</span> : null}
            </button>
          )
        })}
      </div>

      <fieldset className="plan-checkout__methods">
        <legend>Forma de pagamento</legend>
        {METHODS.map((m) => (
          <label key={m.id} className="plan-checkout__method">
            <input type="radio" name="billing-method" value={m.id} checked={method === m.id}
              onChange={() => setMethod(m.id)} />
            <span><strong>{m.label}</strong><small>{m.hint}</small></span>
          </label>
        ))}
      </fieldset>

      {prices.isError ? (
        <p role="status">Não foi possível carregar os preços.{" "}
          <Button variant="ghost" onClick={() => void prices.refetch()}>Tentar novamente</Button></p>
      ) : (
        <div className="plan-checkout__cards">
          {TIERS.map((t) => {
            const price = priceFor(prices.data?.prices, t.id, period)
            const isCurrent = currentTier === t.id
            return (
              <article key={t.id} className={`plan-checkout__card${t.id === "pro" ? " plan-checkout__card--rec" : ""}`}
                aria-busy={prices.isPending}>
                <PlanTag tier={t.id}>{t.label}</PlanTag>
                {price ? (<>
                  <p className="plan-checkout__price"><strong>{brl(price.per_month_cents)}</strong><span>/mês</span></p>
                  <p className="plan-checkout__total">
                    {price.months === 1 ? "Cobrado todo mês" : `${brl(price.total_cents)} a cada ${PERIODS.find((p) => p.id === period)?.label}`}
                  </p>
                  {price.savings_cents > 0 && <p className="plan-checkout__save">Economia de {brl(price.savings_cents)}</p>}
                </>) : <p className="plan-checkout__price">…</p>}
                <Button disabled={!price || isCurrent || checkout.isPending}
                  onClick={() => checkout.mutate(t.id)}>
                  {isCurrent ? "Seu plano" : checkout.isPending && checkout.variables === t.id ? "Abrindo pagamento…" : `Assinar ${t.label}`}
                </Button>
              </article>
            )
          })}
        </div>
      )}


      {error && <p className="plan-checkout__error" role="alert">{error.message}
        {needsProfile && <> <Link to="/profiles">Completar dados da conta</Link></>}</p>}
      <p className="plan-checkout__fine">
        Pagamento processado pelo Asaas em página segura; o Auto Orbital não vê os dados do cartão.
        Renovação automática no fim de cada período; cancele quando quiser, o plano segue até o fim do período pago.
      </p>
    </div>
  )
}
