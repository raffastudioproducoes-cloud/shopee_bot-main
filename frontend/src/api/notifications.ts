import { api } from '../lib/api'

export interface Notification {
  id: number
  type: string | null
  description: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface NotificationsResponse {
  data: Notification[]
  next_cursor: string | null
}

export const notificationsApi = {
  async list(params?: { cursor?: string; limit?: number }): Promise<NotificationsResponse> {
    const searchParams = new URLSearchParams()
    if (params?.cursor) searchParams.append('cursor', params.cursor)
    if (params?.limit) searchParams.append('limit', String(params.limit))

    const query = searchParams.toString()
    return api.get<NotificationsResponse>(`/notifications${query ? `?${query}` : ''}`)
  },
}
