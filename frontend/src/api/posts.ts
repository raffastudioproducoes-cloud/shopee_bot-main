import { api } from '../lib/api'

export interface PostProduct {
  id: number
  product_id: string
  name: string
  image: string | null
  price_min: number | string | null
  price_max: number | string | null
  commission: number | string | null
}

export interface PostMedia {
  id: number
  file_name: string
  size: number
  type: 'IMAGE' | 'VIDEO'
}

export type PostNetwork = 'threads' | 'x' | 'facebook' | 'instagram' | 'tiktok'

export interface PostScheduleEntry {
  id: string
  trigger: 'date' | 'cron'
  run_date?: string | null
  time?: string | null
  day_of_week?: number | null
  days_of_week?: number[] | null
  start_date?: string | null
}

export interface PostScheduleSlot {
  /** 0=segunda ... 6=domingo; null para publicações antigas por data. */
  day_of_week: number | null
  time: string
  status: 'programado' | 'em execução' | 'postado' | 'erro' | 'erro parcial' | 'sem confirmação'
  last_at: string | null
  /** Causa técnica retornada somente para ADMIN. */
  error?: string | null
}

export interface Post {
  id: number
  text: string
  texts: string[]
  post_id: number | null
  user_id: number
  created_at: string
  updated_at: string | null
  products: PostProduct[]
  medias: PostMedia[]
  scheduled: boolean
  publish_immediately?: boolean
  schedule_entries?: PostScheduleEntry[]
  schedule_slots?: PostScheduleSlot[]
  last_published_at?: string | null
  schedule_trigger?: 'date' | 'cron' | null
  scheduled_for?: string | null
  parts_count?: number
  network?: PostNetwork
  /** Mesmo UUID nos posts de um envio multi-rede (null em posts antigos). */
  group_id?: string | null
  /** Resultado real da última execução (o /publish só dispara o job). */
  last_result?: PostPublishResult | null
}

export interface PostPublishResult {
  status: 'published' | 'failed' | 'running' | 'unknown' | 'retry_pending' | 'manual_confirmed' | 'reported_removed' | null
  /** Houve falha HTTP depois de ao menos uma parte enviada; a fila segue unknown. */
  partial_failure?: boolean
  at: string | null
  error: string | null
  proof_url?: string | null
  /** Identificador exato da ocorrência incerta para evitar reenvio com lista desatualizada. */
  job_id?: string | null
}

export interface PostSchedule {
  trigger: 'date' | 'cron'
  run_date?: string | null // ISO 8601, obrigatório se trigger=date
  time?: string | null // "HH:MM", obrigatório se trigger=cron
  times?: string[] | null // até cinco horários por dia escolhido
  day_of_week?: number | null // 0-6, obrigatório se trigger=cron
  days_of_week?: number[] | null // 0-6, um a sete dias para trigger=cron
  start_date?: string | null // ISO 8601, opcional em cron
}

export interface PostCreate {
  texts: string[]
  product_ids?: number[]
  schedule: PostSchedule
  network?: PostNetwork
  /** Multi-rede: mídia já enviada pro 1º post do grupo, reaproveitada. */
  media_ids?: number[]
  group_id?: string
}

export interface MediaDraft {
  id: string
  file_name: string
  size_bytes: number
  media_type: 'IMAGE' | 'VIDEO'
  profile_id: string
  status: 'uploading' | 'ready' | 'consumed' | 'delete_failed'
  expires_at: string
  created_at?: string
}

export interface PostComposition {
  network: PostNetwork
  texts: string[]
}

export interface PostBatchCreate {
  compositions: PostComposition[]
  product_ids?: number[]
  draft_media_ids?: string[]
  schedule: PostSchedule
  publish_immediately?: boolean
}

export interface PostCompositionPlan {
  network: PostNetwork
  texts: string[]
  mode: 'none' | 'single_image' | 'carousel' | 'video' | 'text_only' | 'blocked'
  media_draft_ids: string[]
  warnings: string[]
  blocked_reason?: string | null
  /** Mídias que a rede não recebe, com o motivo (campo opcional). */
  dropped?: Array<{ id: string; name: string; reason: string }>
}

export interface PostBatchResult {
  group_id: string | null
  created: Array<{
    network: PostNetwork
    post_id: number
    mode: PostCompositionPlan['mode']
    warnings: string[]
    medias: PostMedia[]
  }>
  blocked: PostCompositionPlan[]
}

/** Um texto por faixa de limite das redes marcadas (o 1º é o principal). */
export interface GeneratedVariant {
  key: string
  max_chars: number
  networks: PostNetwork[]
  text: string
  over_limit: boolean
  issues: string[]
  /** A IA ultrapassou algum limite; texto corrigido e validado no servidor. */
  adjusted?: boolean
}

export interface GeneratedCopyResult {
  text: string
  variants: GeneratedVariant[]
  /** Apenas os textos efetivamente gerados nesta chamada. */
  parts: string[]
  /** Índice inicial em texts[]; no append preserva as partes anteriores. */
  start_index: number
}

export interface GenerateCopyOptions {
  partCount?: number
  mode?: "full" | "append"
  existingTexts?: string[]
}

export interface PostUpdate {
  texts: string[]
  product_ids?: number[]
}

export interface PostsResponse {
  data: Post[]
  next_cursor: string | null
}

export const postsApi = {
  async list(params?: { cursor?: string; limit?: number }): Promise<PostsResponse> {
    const searchParams = new URLSearchParams()
    if (params?.cursor) searchParams.append('cursor', params.cursor)
    if (params?.limit) searchParams.append('limit', String(params.limit))

    const query = searchParams.toString()
    return api.get<PostsResponse>(`/posts${query ? `?${query}` : ''}`)
  },

  async create(data: PostCreate): Promise<Post> {
    return api.post<Post>('/posts', data)
  },

  async uploadDraftMedia(file: File): Promise<MediaDraft> {
    return api.upload<MediaDraft>('/posts/media-drafts', file)
  },

  async importProductImageDraft(productId: number): Promise<MediaDraft> {
    return api.post<MediaDraft>('/posts/product-image-drafts/' + productId, {})
  },

  async deleteDraftMedia(id: string): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/posts/media-drafts/${id}`)
  },

  async preview(data: PostBatchCreate): Promise<{ plans: PostCompositionPlan[] }> {
    return api.post<{ plans: PostCompositionPlan[] }>('/posts/preview', data)
  },

  async createBatch(data: PostBatchCreate): Promise<PostBatchResult> {
    return api.post<PostBatchResult>('/posts/batch', data)
  },

  async get(id: number): Promise<Post> {
    return api.get<Post>(`/posts/${id}`)
  },

  async update(id: number, data: PostUpdate): Promise<Post> {
    return api.put<Post>(`/posts/${id}`, data)
  },

  async delete(id: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/posts/${id}`)
  },

  async generateCopy(
    productId: number,
    persona: string,
    networks: PostNetwork[] = [],
    options: GenerateCopyOptions = {},
  ): Promise<GeneratedCopyResult> {
    return api.post<GeneratedCopyResult>('/posts/generate-copy', {
      product_id: productId,
      persona,
      networks,
      part_count: options.partCount ?? 1,
      mode: options.mode ?? "full",
      existing_texts: options.existingTexts ?? [],
    })
  },

  async publishNow(id: number): Promise<{ msg: string }> {
    return api.post<{ msg: string }>(`/posts/${id}/publish`, {})
  },

  async reconcile(id: number, payload: { permalink?: string; reported_removed?: boolean }): Promise<{ status: string; proof_url?: string; msg: string }> {
    return api.post(`/posts/${id}/reconcile`, { ...payload, confirmed: true })
  },

  async retryUnknown(id: number, sourceJobId: string): Promise<{ status: string; msg: string }> {
    return api.post(`/posts/${id}/retry-unknown`, {
      source_job_id: sourceJobId,
      confirmed_not_published: true,
      accepts_duplicate_risk: true,
    })
  },

  async uploadMedia(postId: number, file: File): Promise<PostMedia> {
    return api.upload<PostMedia>(`/posts/${postId}/media`, file)
  },

  async deleteMedia(postId: number, mediaId: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/posts/${postId}/media/${mediaId}`)
  },
}
