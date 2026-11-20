import { api } from '../lib/api'

export type ShopeeVideoStatus = {
  configured: boolean
  connected: boolean
  token_valid: boolean
  /** Token expirado sem renovação possível: o usuário precisa autorizar de novo. */
  needs_reconnect?: boolean
  sandbox: boolean | null
  publishing_enabled: boolean
}

/** Resultado do ping somente leitura (HTTP 200 nos três casos). */
export type ShopeeVideoTestResult =
  | { ok: true; http_reachable: true; videos_returned: number; response_keys: string[]; sandbox: boolean; host: string }
  | { ok: false; http_reachable: true; shopee_error: string; shopee_message: string; request_id: string }
  | { ok: false; http_reachable: false; error: string }

export type AdminShopeeVideoStatus = {
  configured: boolean
  partner_id: number | null
  sandbox: boolean
  callback_configured: boolean
}

export const shopeeVideoApi = {
  status: () => api.get<ShopeeVideoStatus>('/shopee-video/status'),
  authorize: () => api.get<{ url: string }>('/shopee-video/authorize'),
  refresh: () => api.post<{ connected: boolean; token_valid: boolean }>('/shopee-video/refresh', {}),
  testConnection: () => api.post<ShopeeVideoTestResult>('/shopee-video/test-connection', {}),
  disconnect: () => api.delete<{ connected: boolean }>('/shopee-video/authorization'),
  preview: (input: {
    caption: string; product_item_ids: number[]; video_seconds: number
    video_bytes: number; aigc_label: boolean
  }) => api.post<{ valid: boolean; message: string; product_count: number }>('/shopee-video/preview', input),
}

export const adminShopeeVideoApi = {
  status: () => api.get<AdminShopeeVideoStatus>('/admin/shopee-video'),
  save: (partner_id: number, partner_key: string, sandbox: boolean) =>
    api.put<{ configured: boolean }>('/admin/shopee-video', { partner_id, partner_key, sandbox }),
}
