import { api } from '../lib/api'

export type UserAccess = 'USER' | 'ADMIN'

export interface AppUser {
  id: string
  username: string
  access: UserAccess
  created_at: string
  updated_at: string | null
  plan_tier: 'free' | 'pro' | 'premium'
  /** Fim do período pago/concedido; null para Free, sem prazo ou ADMIN. */
  plan_expires_at: string | null
}

export type GrantablePlan = 'free' | 'pro' | 'premium'

export interface PlanGrantInput {
  plan: GrantablePlan
  days?: number
  ends_at?: string
  reason?: string
}

export interface PlanGrantResult {
  user_id: string
  plan_tier: GrantablePlan
  plan_expires_at: string | null
}

export interface UserCreate {
  username: string
  password: string
  access: UserAccess
}

export interface UserUpdate {
  username: string
  access: UserAccess
}

export interface UsersResponse {
  data: AppUser[]
  next_cursor: string | null
}

export const usersApi = {
  async list(params?: { cursor?: string; limit?: number }): Promise<UsersResponse> {
    const searchParams = new URLSearchParams()
    if (params?.cursor) searchParams.append('cursor', params.cursor)
    if (params?.limit) searchParams.append('limit', String(params.limit))

    const query = searchParams.toString()
    return api.get<UsersResponse>(`/admin/users${query ? `?${query}` : ''}`)
  },

  async create(data: UserCreate): Promise<AppUser> {
    return api.post<AppUser>('/admin/users', data)
  },

  async get(id: string): Promise<AppUser> {
    return api.get<AppUser>(`/admin/users/${id}`)
  },

  async update(id: string, data: UserUpdate): Promise<AppUser> {
    return api.put<AppUser>(`/admin/users/${id}`, data)
  },

  async delete(id: string): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/admin/users/${id}`)
  },

  async setPlan(id: string, data: PlanGrantInput): Promise<PlanGrantResult> {
    return api.put<PlanGrantResult>('/admin/users/' + id + '/plan', data)
  },

  async deleteSelf(currentPassword: string): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>('/users/me', { current_password: currentPassword })
  },

  async exportBackup(): Promise<BackupData> {
    return api.get<BackupData>('/users/me/backup')
  },

  async restoreBackup(data: BackupData): Promise<{ msg: string }> {
    return api.post<{ msg: string }>('/users/me/restore', data)
  },
}

export interface BackupData {
  products: Record<string, unknown>[]
  product_lists: Record<string, unknown>[]
  posts: Record<string, unknown>[]
  exported_at: string
  checksum: string
}
