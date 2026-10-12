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
  parts_count?: number
  network?: PostNetwork
  /** Mesmo UUID nos posts de um envio multi-rede (null em posts antigos). */
  group_id?: string | null
  /** Resultado real da última execução (o /publish só dispara o job). */
  last_result?: PostPublishResult | null
}

export interface PostPublishResult {
  status: 'published' | 'failed' | null
  at: string | null
  error: string | null
}

export interface PostSchedule {
  trigger: 'date' | 'cron'
  run_date?: string | null // ISO 8601, obrigatório se trigger=date
  time?: string | null // "HH:MM", obrigatório se trigger=cron
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
}

export interface PostCompositionPlan {
  network: PostNetwork
  texts: string[]
  mode: 'none' | 'single_image' | 'carousel' | 'video' | 'text_only' | 'blocked'
  media_draft_ids: string[]
  warnings: string[]
  blocked_reason?: string | null
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
  ): Promise<{ text: string; variants: GeneratedVariant[] }> {
    return api.post<{ text: string; variants: GeneratedVariant[] }>('/posts/generate-copy', {
      product_id: productId,
      persona,
      networks,
    })
  },

  async publishNow(id: number): Promise<{ msg: string }> {
    return api.post<{ msg: string }>(`/posts/${id}/publish`, {})
  },

  async uploadMedia(postId: number, file: File): Promise<PostMedia> {
    return api.upload<PostMedia>(`/posts/${postId}/media`, file)
  },

  async deleteMedia(postId: number, mediaId: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/posts/${postId}/media/${mediaId}`)
  },
}
