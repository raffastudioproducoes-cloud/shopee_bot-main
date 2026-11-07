import { api } from '../lib/api'

export type ShopeeVideoStatus = {
  configured: boolean
  connected: boolean
  token_valid: boolean
  sandbox: boolean | null
  publishing_enabled: boolean
}

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
