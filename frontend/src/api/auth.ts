import { api, ApiError } from '../lib/api'
import { formatApiError } from '../lib/apiError'

export interface User {
  id: number
  username: string
  access: string
}

export interface LoginResponse {
  msg: string
}

export interface MeResponse {
  id: number
  username: string
  access: string
  /** Perfil ativo validado pelo backend (claim do cookie); null = sem perfil/token antigo. */
  profile_id: string | null
}

export interface ResetPasswordResponse {
  msg: string
}

export interface RegisterResponse {
  id: number
  username: string
  access: string
}

export const authApi = {
  async login(username: string, password: string): Promise<string> {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await fetch('/api/auth/login', {
      method: 'POST',
      body: formData,
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro no login' }))
      throw new ApiError(response.status, formatApiError(error, response.status))
    }

    const data = await response.json()
    return data.msg
  },

  async logout(): Promise<void> {
    const response = await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro no logout' }))
      throw new ApiError(response.status, formatApiError(error, response.status))
    }
  },

  async me(): Promise<MeResponse> {
    return api.get<MeResponse>('/auth/me')
  },

  async resetPassword(
    username: string,
    currentPassword: string,
    newPassword: string
  ): Promise<string> {
    const data = await api.post<ResetPasswordResponse>('/auth/reset-password', {
      username,
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data.msg
  },

  async register(username: string, password: string): Promise<RegisterResponse> {
    return api.post<RegisterResponse>('/auth/register', { username, password })
  },
}