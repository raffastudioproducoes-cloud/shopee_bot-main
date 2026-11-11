import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { billingApi, type BillingType, type PlanPrice } from "../../api/billing"
import { ApiError } from "../../lib/api"
import {
  BILLING_PERIODS, PAID_TIERS, PERIOD_LABELS, PERIOD_MONTHS, brl, discountLabel,
  type BillingPeriod, type PaidTier,
} from "../../lib/planIntent"
import { plans as planLimits } from "../../pages/presentation/content"
import { Button } from "../ui/Button"
import { PlanTag } from "./PlanTag"
import "./planCheckout.css"

const TIER_NAMES: Record<PaidTier, string> = { pro: "Pro", premium: "Premium" }
const METHODS: { id: BillingType; label: string; hint: string }[] = [
  { id: "CREDIT_CARD", label: "Cartão de crédito", hint: "Renova sozinho no cartão a cada ciclo." },
  { id: "PIX", label: "Pix", hint: "A cada ciclo chega uma fatura Pix para você pagar." },
]

export function priceFor(prices: PlanPrice[] | undefined, tier: PaidTier, period: BillingPeriod) {
  return prices?.find((p) => p.tier === tier && p.period === period)
}

function highlights(tier: PaidTier): string[] {
  const p = planLimits.find((x) => x.id === tier)
  if (!p) return []
  return [
    `${p.products.toLocaleString("pt-BR")} produtos`,
    `${p.profiles} perfis`,
    `${p.postsPerHour} envios por hora`,
    p.campaign ? `Campanhas: até ${p.campaign.active} ativas por perfil` : "Sem campanhas",
    ...(p.automation ? ["Automação de posts"] : []),
  ]
}

function renewalDate(period: BillingPeriod): string {
  const d = new Date()
  d.setMonth(d.getMonth() + PERIOD_MONTHS[period])
  return d.toLocaleDateString("pt-BR")
}

interface Props {
  initialTier?: PaidTier
  initialPeriod?: BillingPeriod
  currentTier?: string
  /** Já existe assinatura aberta: contratar de novo geraria cobrança em duplicidade. */
  hasSubscription?: boolean
}

export function PlanCheckout({ initialTier, initialPeriod, currentTier, hasSubscription = false }: Props) {
  const [tier, setTier] = useState<PaidTier>(initialTier ?? "pro")
  const [period, setPeriod] = useState<BillingPeriod>(initialPeriod ?? "yearly")
  const [method, setMethod] = useState<BillingType>("CREDIT_CARD")
  const prices = useQuery({ queryKey: ["billing-plans"], queryFn: billingApi.plans, staleTime: 5 * 60_000 })
  const enabled = prices.data?.checkout_enabled === true
  const checkout = useMutation({
    mutationFn: () => billingApi.checkout({ tier, period, billing_type: method }),
    onSuccess: (data) => { window.location.assign(data.checkout_url) },
  })
  const error = checkout.error instanceof ApiError ? checkout.error : null
  const needsProfile = error?.status === 422 && error.message.startsWith("Complete os dados")
  const selected = priceFor(prices.data?.prices, tier, period)
  const alreadyThis = currentTier === tier
  const blocked = !enabled || !selected || alreadyThis || hasSubscription

  return (
    <section className="plan-checkout" aria-labelledby="plan-checkout-title">
      <h2 id="plan-checkout-title">Escolha seu plano</h2>

      <div className="plan-checkout__periods" role="radiogroup" aria-label="Período de contratação">
        {BILLING_PERIODS.map((id) => {
          const bps = priceFor(prices.data?.prices, "pro", id)?.discount_bps ?? 0
          return (
            <button key={id} type="button" role="radio" aria-checked={period === id}
              className="plan-checkout__period" onClick={() => setPeriod(id)}>
              {PERIOD_LABELS[id]}{bps ? <span className="plan-checkout__off">{discountLabel(bps)}</span> : null}
            </button>
          )
        })}
      </div>

      {prices.isError ? (
        <p role="status">Não foi possível carregar os preços.{" "}
          <Button variant="ghost" onClick={() => void prices.refetch()}>Tentar novamente</Button></p>
      ) : (
        <div className="plan-checkout__cards" role="radiogroup" aria-label="Plano">
          {PAID_TIERS.map((id) => {
            const price = priceFor(prices.data?.prices, id, period)
            return (
              <button key={id} type="button" role="radio" aria-checked={tier === id}
                className={`plan-checkout__card${id === "pro" ? " plan-checkout__card--rec" : ""}`}
                aria-busy={prices.isPending} onClick={() => setTier(id)}>
                <span className="plan-checkout__card-head">
                  <PlanTag tier={id}>{TIER_NAMES[id]}</PlanTag>
                  {currentTier === id ? <small className="plan-checkout__you">Seu plano</small>
                    : id === "pro" ? <small className="plan-checkout__rec">Mais equilibrado</small> : null}
                </span>
                {price ? (<>
                  <span className="plan-checkout__price"><strong>{brl(price.per_month_cents)}</strong><span>/mês</span></span>
                  <span className="plan-checkout__total">
                    {price.months === 1 ? "Cobrado todo mês" : `${brl(price.total_cents)} a cada ${PERIOD_LABELS[period].toLowerCase()}`}
                  </span>
                  {price.savings_cents > 0 && <span className="plan-checkout__save">Economia de {brl(price.savings_cents)}</span>}
                </>) : <span className="plan-checkout__price">…</span>}
                <ul className="plan-checkout__list">{highlights(id).map((h) => <li key={h}>{h}</li>)}</ul>
              </button>
            )
          })}
        </div>
      )}

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

      <div className="plan-checkout__summary" aria-live="polite">
        <h3>Resumo</h3>
        {selected ? (
          <dl>
            <dt>Plano</dt><dd>{TIER_NAMES[tier]} · {PERIOD_LABELS[period]}</dd>
            <dt>Total hoje</dt><dd><strong>{brl(selected.total_cents)}</strong></dd>
            <dt>Renovação</dt><dd>automática, a próxima por volta de {renewalDate(period)}</dd>
            <dt>Pagamento</dt><dd>{METHODS.find((m) => m.id === method)?.label}</dd>
          </dl>
        ) : <p>Carregando preços…</p>}
        <Button disabled={blocked || checkout.isPending} onClick={() => checkout.mutate()}>
          {checkout.isPending ? "Abrindo pagamento…" : alreadyThis ? "Este já é o seu plano" : "Ir para o pagamento seguro"}
        </Button>
        {prices.data && !enabled && <p className="plan-checkout__note" role="status">
          A contratação ainda não está aberta. Assim que abrir, este botão libera o pagamento.</p>}
        {hasSubscription && <p className="plan-checkout__note" role="status">
          Você já tem uma assinatura. Para trocar de plano, cancele a atual (ela vale até o fim do período pago)
          e contrate o novo plano em seguida.</p>}
      </div>

      {error && <p className="plan-checkout__error" role="alert">{error.message}
        {needsProfile && <> <Link to="/profiles">Completar dados da conta</Link></>}</p>}
      <p className="plan-checkout__fine">
        O pagamento acontece na página segura do Asaas; o Auto Orbital não vê os dados do seu cartão.
        A assinatura renova sozinha no fim de cada período e você pode cancelar quando quiser: o plano segue até o fim
        do período já pago. O plano é liberado quando o Asaas confirma o pagamento, o que pode levar alguns minutos.
        Veja os <Link to="/termos">Termos</Link> e a <Link to="/privacidade">Política de Privacidade</Link>.
      </p>
    </section>
  )
}
