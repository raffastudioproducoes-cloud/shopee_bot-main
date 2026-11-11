import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { billingApi, type MySubscription } from "../../api/billing"
import { PERIOD_LABELS, brl } from "../../lib/planIntent"
import { Button } from "../ui/Button"
import { PlanTag } from "./PlanTag"
import "./planCheckout.css"

const TIER_NAMES = { pro: "Pro", premium: "Premium" } as const
const STATUS_LABELS: Record<string, string> = {
  pending: "Aguardando o primeiro pagamento", active: "Ativa", overdue: "Em atraso", canceled: "Cancelada",
}
const PAYMENT_LABELS: Record<string, string> = {
  PENDING: "Aguardando pagamento", AWAITING_RISK_ANALYSIS: "Em análise", CONFIRMED: "Pago", RECEIVED: "Pago",
  RECEIVED_IN_CASH: "Pago", OVERDUE: "Vencida", REFUNDED: "Estornada", PARTIALLY_REFUNDED: "Estorno parcial",
  REFUND_REQUESTED: "Estorno solicitado", REFUND_IN_PROGRESS: "Estorno em andamento",
  CHARGEBACK_REQUESTED: "Contestada (chargeback)", CHARGEBACK_DISPUTE: "Em disputa",
  PAYMENT_CREATED: "Aguardando pagamento", PAYMENT_UPDATED: "Atualizada", PAYMENT_DELETED: "Removida",
}
const METHOD_LABELS: Record<string, string> = { CREDIT_CARD: "Cartão", PIX: "Pix", BOLETO: "Boleto", UNDEFINED: "—" }

const day = (iso: string | null) => (iso ? new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR") : "—")

/** Só abre fatura hospedada no Asaas; qualquer outro endereço vira texto, nunca link. */
export function safeInvoiceUrl(url: string | null): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    return u.protocol === "https:" && (u.hostname === "asaas.com" || u.hostname.endsWith(".asaas.com")) ? u.href : null
  } catch {
    return null
  }
}

export function SubscriptionCard() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ["billing-subscription"], queryFn: billingApi.subscription, retry: false })
  const [confirming, setConfirming] = useState(false)
  const cancel = useMutation({
    mutationFn: billingApi.cancelSubscription,
    onSuccess: (data: MySubscription) => {
      queryClient.setQueryData(["billing-subscription"], data)
      setConfirming(false)
    },
  })
  const sub = query.data?.subscription
  const payments = query.data?.payments ?? []
  if (query.isPending || query.isError || (!sub && payments.length === 0)) return null

  const open = sub && sub.status !== "canceled"
  return (
    <section className="plan-checkout plan-sub" aria-labelledby="plan-sub-title">
      <h2 id="plan-sub-title">Minha assinatura</h2>
      {sub && (
        <dl className="plan-sub__grid">
          <dt>Plano</dt><dd><PlanTag tier={sub.tier}>{TIER_NAMES[sub.tier]}</PlanTag> · {PERIOD_LABELS[sub.period]}</dd>
          <dt>Situação</dt><dd>{STATUS_LABELS[sub.status] ?? sub.status}</dd>
          <dt>Valor do ciclo</dt><dd>{brl(sub.value_cents)} · {METHOD_LABELS[sub.billing_type] ?? sub.billing_type}</dd>
          {sub.status === "canceled"
            ? <><dt>Plano vale até</dt><dd>{day(sub.current_period_end)}</dd></>
            : sub.current_period_end && <><dt>Paga até</dt><dd>{day(sub.current_period_end)}</dd></>}
        </dl>
      )}
      {sub?.status === "overdue" && (
        <p className="plan-checkout__note" role="status">
          Há uma cobrança em atraso. Seu plano continua ativo até {day(sub.grace_until)} ({sub.grace_days} dias de
          tolerância); depois disso a conta volta para o plano Free. Pague a fatura abaixo para manter o plano.
        </p>
      )}
      {sub?.status === "canceled" && (
        <p className="plan-checkout__note" role="status">
          A renovação foi cancelada. O plano continua até {day(sub.current_period_end)} e não será cobrado de novo.
        </p>
      )}

      {payments.length > 0 && (
        <div className="plan-sub__scroll" tabIndex={0} aria-label="Histórico de cobranças">
          <table>
            <thead><tr><th scope="col">Vencimento</th><th scope="col">Valor</th><th scope="col">Forma</th><th scope="col">Situação</th><th scope="col">Fatura</th></tr></thead>
            <tbody>
              {payments.map((p, i) => {
                const link = safeInvoiceUrl(p.invoice_url)
                return (
                  <tr key={`${p.due_date}-${i}`}>
                    <td>{day(p.due_date)}</td>
                    <td>{p.value_cents === null ? "—" : brl(p.value_cents)}</td>
                    <td>{METHOD_LABELS[p.billing_type ?? ""] ?? "—"}</td>
                    <td>{PAYMENT_LABELS[p.status] ?? p.status}</td>
                    <td>{link ? <a href={link} target="_blank" rel="noopener noreferrer">Abrir</a> : "—"}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {open && !confirming && (
        <Button variant="ghost" onClick={() => setConfirming(true)}>Cancelar assinatura</Button>
      )}
      {open && confirming && (
        <div className="plan-sub__confirm" role="alertdialog" aria-label="Confirmar cancelamento">
          <p>Cancelar agora? Seu plano continua até {day(sub.current_period_end)} e depois volta para o Free.
            Cobranças pendentes desta assinatura são removidas.</p>
          <div className="plan-sub__actions">
            <Button variant="ghost" onClick={() => setConfirming(false)} disabled={cancel.isPending}>Manter assinatura</Button>
            <Button onClick={() => cancel.mutate()} disabled={cancel.isPending}>
              {cancel.isPending ? "Cancelando…" : "Sim, cancelar"}
            </Button>
          </div>
        </div>
      )}
      {cancel.error && <p className="plan-checkout__error" role="alert">{cancel.error.message}</p>}
    </section>
  )
}
