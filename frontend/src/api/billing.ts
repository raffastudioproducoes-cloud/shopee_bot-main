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

export interface BillingAdminStatus {
  environment: "sandbox" | "production"
  api_key_configured: boolean
  webhook_token_configured: boolean
  sandbox_testers: number
  webhook_url: string
  webhook: { id?: string; enabled?: boolean; interrupted?: boolean; error?: string } | null
}

export const billingAdminApi = {
  status: () => api.get<BillingAdminStatus>("/admin/billing/status"),
  registerWebhook: () => api.post<{ id: string; url: string; updated: boolean; events: number }>("/admin/billing/webhook", {}),
}
