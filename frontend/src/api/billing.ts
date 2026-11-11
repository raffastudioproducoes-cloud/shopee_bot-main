import { api } from "../lib/api"

export type PaidTier = "pro" | "premium"
export type BillingPeriod = "monthly" | "quarterly" | "semiannual" | "yearly"
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

export interface CheckoutResponse { checkout_url: string; expires_in_minutes: number; value_cents: number }

export const billingApi = {
  plans: () => api.get<{ currency: "BRL"; prices: PlanPrice[] }>("/billing/plans"),
  checkout: (body: { tier: PaidTier; period: BillingPeriod; billing_type: BillingType }) =>
    api.post<CheckoutResponse>("/billing/checkout", body),
}
