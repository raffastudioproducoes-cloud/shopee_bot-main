// Somente a área /admin importa este arquivo.
import { api } from "../lib/api"

export interface BillingAdminStatus {
  /** null quando não há chave de API: sem chave não existe ambiente de cobrança. */
  environment: "sandbox" | "production" | null
  /** Para onde ASAAS_API_URL aponta (o padrão, sem a variável, é o sandbox). */
  api_url_environment: "sandbox" | "production"
  /** Ambiente indicado pelo prefixo da chave; null se o formato não diz. */
  key_environment: "sandbox" | "production" | null
  environment_mismatch: boolean
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
