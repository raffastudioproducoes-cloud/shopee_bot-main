import { api } from '../lib/api'

export interface PostProduct {
  id: number
  product_id: string
  name: string
  image: string | null
  price_min: number | null
  price_max: number | null
  commission: number | null
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
}

export interface PostSchedule {
  trigger: 'date' | 'cron'
  run_date?: string | null // ISO 8601, obrigatório se trigger=date
  time?: string | null // "HH:MM", obrigatório se trigger=cron
  day_of_week?: number | null // 0-6, obrigatório se trigger=cron
  start_date?: string | null // ISO 8601, opcional em cron
}

export interface PostCreate {
  texts: string[]
  product_ids?: number[]
  schedule: PostSchedule
  network?: PostNetwork
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

  async get(id: number): Promise<Post> {
    return api.get<Post>(`/posts/${id}`)
  },

  async update(id: number, data: PostUpdate): Promise<Post> {
    return api.put<Post>(`/posts/${id}`, data)
  },

  async delete(id: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/posts/${id}`)
  },

  async generateCopy(productId: number, persona: string): Promise<{ text: string }> {
    return api.post<{ text: string }>('/posts/generate-copy', {
      product_id: productId,
      persona,
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
