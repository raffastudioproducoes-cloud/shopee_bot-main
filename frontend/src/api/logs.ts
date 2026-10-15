import { api } from '../lib/api'

export interface LogEntry {
  id: number
  user_id: string | null
  username: string | null
  method: string
  path: string
  action: string | null
  status_code: number | null
  duration_ms: number | null
  error: string | null
  redirect_to: string | null
  created_at: string
}

export interface LogsResponse {
  data: LogEntry[]
  total: number
  limit: number
  offset: number
}

export interface LogsFilters {
  limit?: number
  offset?: number
  user_id?: string // UUID
  username?: string
  status_code?: number
  created_from?: string
  created_to?: string
}

export const logsApi = {
  async list(filters?: LogsFilters): Promise<LogsResponse> {
    const params = new URLSearchParams()
    if (filters?.limit) params.append('limit', String(filters.limit))
    if (filters?.offset) params.append('offset', String(filters.offset))
    if (filters?.user_id) params.append('user_id', String(filters.user_id))
    if (filters?.username) params.append('username', filters.username)
    if (filters?.status_code) params.append('status_code', String(filters.status_code))
    if (filters?.created_from) params.append('created_from', filters.created_from)
    if (filters?.created_to) params.append('created_to', filters.created_to)

    const query = params.toString()
    return api.get<LogsResponse>(`/admin/logs${query ? `?${query}` : ''}`)
  },
}
