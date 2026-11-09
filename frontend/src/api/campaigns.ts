import { api } from '../lib/api'

/** Previsão inerte; somente o endpoint activate materializa a campanha. */
export interface CampaignPreviewRequest {
  list_id: number
  item_ids: number[]
  start_date: string
  end_date: string
  weekdays: number[]
  start_time: string
  end_time: string
  posts_per_day: number
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
  product_media_ids: string[]
}

export interface CampaignDraftSaveRequest {
  name: string
  list_id: number
  items: CampaignDraftItemPayload[]
  schedule: CampaignPreviewRequest | null
}

/** Rascunhos legados podem manter intervalo em minutos até o usuário salvá-los novamente. */
export type SavedCampaignSchedule = Omit<CampaignPreviewRequest, 'posts_per_day'> & {
  posts_per_day?: number
  interval_minutes?: number
}

export interface CampaignDraftRecord {
  id: string
  revision: number
  status: 'draft'
  source_list_id: number | null
  source_list_name: string
  campaign_name: string
  items: Array<CampaignDraftItemPayload & { source_image?: string | null }>
  schedule: SavedCampaignSchedule | null
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

export type CampaignLifecycle = 'preparing' | 'active' | 'paused' | 'cancelled' | 'completed'

export interface CampaignProgress {
  total: number
  planned: number
  running: number
  succeeded: number
  failed: number
  unknown: number
  cancelled: number
}

export interface CampaignReservation {
  id: string
  name: string
  draft_id: string | null
  lifecycle: CampaignLifecycle
  source_environment: 'staging' | 'production' | null
  created_at: string
  activated_at: string | null
  pause_reason: string | null
  progress: CampaignProgress | null
}

export interface CampaignHistoryRow {
  id: string
  product_id: number
  network: string
  planned_at: string
  state: 'planned' | 'running' | 'succeeded' | 'failed' | 'unknown' | 'cancelled'
  finished_at: string | null
  delivery: {
    status: string
    attempt: number
    external_started_at: string | null
    finished_at: string | null
    last_error: string | null
  } | null
}

export const campaignsApi = {
  activateDraft(id: string, expectedRevision: number): Promise<CampaignReservation> {
    return api.post<CampaignReservation>(
      `/campaigns/drafts/${encodeURIComponent(id)}/activate`, { expected_revision: expectedRevision })
  },
  listActive(): Promise<{ data: CampaignReservation[] }> {
    return api.get<{ data: CampaignReservation[] }>('/campaigns/active')
  },
  getActive(id: string): Promise<CampaignReservation> {
    return api.get<CampaignReservation>(`/campaigns/active/${encodeURIComponent(id)}`)
  },
  getHistory(id: string, offset = 0, limit = 10): Promise<{ data: CampaignHistoryRow[], has_more: boolean }> {
    return api.get<{ data: CampaignHistoryRow[], has_more: boolean }>(
      `/campaigns/active/${encodeURIComponent(id)}/history?offset=${offset}&limit=${limit}`)
  },
  changeState(id: string, action: 'pause' | 'resume' | 'cancel'): Promise<CampaignReservation> {
    return api.post<CampaignReservation>(
      `/campaigns/active/${encodeURIComponent(id)}/${action}`, {})
  },
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
  deleteDraft(id: string, expectedRevision: number): Promise<void> {
    return api.delete<void>(`/campaigns/drafts/${encodeURIComponent(id)}?expected_revision=${expectedRevision}`)
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
