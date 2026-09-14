import { api, ApiError } from '../lib/api'

export type UserAccess = 'USER' | 'ADMIN'

export interface AppUser {
  id: string
  username: string
  access: UserAccess
  created_at: string
  updated_at: string | null
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
    return api.get<UsersResponse>(`/users${query ? `?${query}` : ''}`)
  },

  async create(data: UserCreate): Promise<AppUser> {
    return api.post<AppUser>('/users', data)
  },

  async get(id: string): Promise<AppUser> {
    return api.get<AppUser>(`/users/${id}`)
  },

  async update(id: string, data: UserUpdate): Promise<AppUser> {
    return api.put<AppUser>(`/users/${id}`, data)
  },

  async delete(id: string): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/users/${id}`)
  },
}

export { ApiError }
