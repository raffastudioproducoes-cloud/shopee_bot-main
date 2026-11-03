import { api } from '../lib/api'

/** Rascunho/solicitação de prévia; a rota nunca ativa uma campanha. */
export interface CampaignPreviewRequest {
  list_id: number
  item_ids: number[]
  start_date: string
  end_date: string
  weekdays: number[]
  start_time: string
  end_time: string
  interval_minutes: number
}

export interface CampaignPreviewSlot {
  sequence: number
  product_id: number
  scheduled_local: string
  scheduled_utc: string
}

export interface CampaignPreviewResponse {
  list_id: number
  list_name: string
  product_count: number
  slot_count: number
  uncovered_item_ids: number[]
  uncovered_count: number
  truncated: boolean
  slots: CampaignPreviewSlot[]
  timezone: string
  activated: false
  message: string
}


/** F3A: conteúdo independente por produto. Não publica nem reserva horários. */
export interface CampaignDraftItemPayload {
  product_id: number
  title: string
  copy: string
  affiliate_link: string
  networks: Array<'threads' | 'x' | 'facebook' | 'instagram' | 'tiktok'>
  network_copies: Partial<Record<'threads' | 'x' | 'facebook' | 'instagram' | 'tiktok', string>>
  use_shopee_image: boolean
}

export interface CampaignDraftSaveRequest {
  name: string
  list_id: number
  items: CampaignDraftItemPayload[]
  schedule: CampaignPreviewRequest | null
}

export interface CampaignDraftRecord {
  id: string
  revision: number
  status: 'draft'
  source_list_id: number | null
  source_list_name: string
  campaign_name: string
  items: Array<CampaignDraftItemPayload & { source_image?: string | null }>
  schedule: CampaignPreviewRequest | null
  updated_at: string
}

export interface CampaignMediaRecord {
  id: string
  product_id: number
  slot: number
  file_name: string
  media_type: 'IMAGE' | 'VIDEO'
  size_bytes: number
  status: 'ready'
  created_at: string
}

export const campaignsApi = {
  preview(data: CampaignPreviewRequest): Promise<CampaignPreviewResponse> {
    return api.post<CampaignPreviewResponse>('/campaigns/preview', data)
  },
  listDrafts(): Promise<{ data: CampaignDraftRecord[] }> {
    return api.get<{ data: CampaignDraftRecord[] }>('/campaigns/drafts')
  },
  getDraft(id: string): Promise<CampaignDraftRecord> {
    return api.get<CampaignDraftRecord>(`/campaigns/drafts/${encodeURIComponent(id)}`)
  },
  createDraft(data: CampaignDraftSaveRequest): Promise<CampaignDraftRecord> {
    return api.post<CampaignDraftRecord>('/campaigns/drafts', data)
  },
  updateDraft(id: string, data: CampaignDraftSaveRequest & { expected_revision: number }): Promise<CampaignDraftRecord> {
    return api.put<CampaignDraftRecord>(`/campaigns/drafts/${encodeURIComponent(id)}`, data)
  },
  listMedia(id: string): Promise<{ data: CampaignMediaRecord[] }> {
    return api.get<{ data: CampaignMediaRecord[] }>(`/campaigns/drafts/${encodeURIComponent(id)}/media`)
  },
  uploadMedia(id: string, productId: number, file: File): Promise<CampaignMediaRecord> {
    return api.upload<CampaignMediaRecord>(
      `/campaigns/drafts/${encodeURIComponent(id)}/items/${productId}/media`, file)
  },
  deleteMedia(id: string, mediaId: string): Promise<void> {
    return api.delete<void>(
      `/campaigns/drafts/${encodeURIComponent(id)}/media/${encodeURIComponent(mediaId)}`)
  },
}
