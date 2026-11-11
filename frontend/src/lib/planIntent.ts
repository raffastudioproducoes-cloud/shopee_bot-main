/** Intenção de compra vinda da apresentação ou de um botão de upgrade. Só valores conhecidos passam:
 *  nada digitado na URL chega à API ou vira destino de navegação. */
export const PAID_TIERS = ["pro", "premium"] as const
export const BILLING_PERIODS = ["monthly", "quarterly", "semiannual", "yearly"] as const
export type PaidTier = (typeof PAID_TIERS)[number]
export type BillingPeriod = (typeof BILLING_PERIODS)[number]

export const RETURN_STATES = ["sucesso", "cancelada", "expirada"] as const
export type ReturnState = (typeof RETURN_STATES)[number]

export interface PlanIntent { plano?: PaidTier; periodo?: BillingPeriod }
export interface PlanosSearch extends PlanIntent { assinatura?: ReturnState; de?: string }

const pick = <T extends string>(value: unknown, allowed: readonly T[]): T | undefined =>
  typeof value === "string" && (allowed as readonly string[]).includes(value) ? (value as T) : undefined

export function parsePlanIntent(search: Record<string, unknown>): PlanIntent {
  const plano = pick(search.plano, PAID_TIERS)
  const periodo = pick(search.periodo, BILLING_PERIODS)
  return { ...(plano ? { plano } : {}), ...(periodo ? { periodo } : {}) }
}

/** `de` diz de onde veio o clique ("produtos", "listas"...); só letras minúsculas e hífen, até 24 caracteres. */
export function parsePlanosSearch(search: Record<string, unknown>): PlanosSearch {
  const assinatura = pick(search.assinatura, RETURN_STATES)
  const de = typeof search.de === "string" && /^[a-z-]{1,24}$/.test(search.de) ? search.de : undefined
  return { ...parsePlanIntent(search), ...(assinatura ? { assinatura } : {}), ...(de ? { de } : {}) }
}

/** Preço em reais no padrão brasileiro. */
export const brl = (cents: number) =>
  (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })

export const discountLabel = (bps: number) => (bps ? `−${(bps / 100).toLocaleString("pt-BR")}%` : "")

export const PERIOD_LABELS: Record<BillingPeriod, string> = {
  monthly: "Mensal", quarterly: "3 meses", semiannual: "6 meses", yearly: "1 ano",
}
export const PERIOD_MONTHS: Record<BillingPeriod, number> = { monthly: 1, quarterly: 3, semiannual: 6, yearly: 12 }
