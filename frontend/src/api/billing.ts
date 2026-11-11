// Somente o que o CLIENTE usa. Rotas de administração ficam em api/billingAdmin.ts
// e só são importadas pela área /admin (não entram no pacote do site do cliente).
import { api } from "../lib/api"
import type { BillingPeriod, PaidTier } from "../lib/planIntent"

export type BillingType = "CREDIT_CARD" | "PIX"

export interface PlanPrice {
  tier: PaidTier
  period: BillingPeriod
  months: number
  discount_bps: number
  monthly_price_cents: number
  total_cents: number
  per_month_cents: number
  savings_cents: number
}

export interface PlansResponse { currency: "BRL"; checkout_enabled: boolean; sandbox?: boolean; prices: PlanPrice[] }
export interface CheckoutResponse { checkout_url: string; expires_in_minutes: number; value_cents: number }

export interface MySubscription {
  subscription: null | {
    tier: PaidTier
    period: BillingPeriod
    billing_type: BillingType
    value_cents: number
    status: "pending" | "active" | "overdue" | "canceled"
    current_period_end: string | null
    overdue_since: string | null
    grace_until: string | null
    grace_days: number
  }
  payments: Array<{
    billing_type: string | null
    status: string
    value_cents: number | null
    due_date: string | null
    paid_at: string | null
    invoice_url: string | null
  }>
}

export const billingApi = {
  plans: () => api.get<PlansResponse>("/billing/plans"),
  checkout: (body: { tier: PaidTier; period: BillingPeriod; billing_type: BillingType }) =>
    api.post<CheckoutResponse>("/billing/checkout", body),
  subscription: () => api.get<MySubscription>("/billing/subscription"),
  cancelSubscription: () => api.post<MySubscription>("/billing/subscription/cancel", {}),
}
