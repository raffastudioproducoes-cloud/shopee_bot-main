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

export const campaignsApi = {
  preview(data: CampaignPreviewRequest): Promise<CampaignPreviewResponse> {
    return api.post<CampaignPreviewResponse>('/campaigns/preview', data)
  },
}
