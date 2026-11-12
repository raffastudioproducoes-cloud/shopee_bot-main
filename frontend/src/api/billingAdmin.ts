// Somente a área /admin importa este arquivo.
import { api } from "../lib/api"

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
