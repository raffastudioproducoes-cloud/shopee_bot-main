import { api } from '../lib/api'

export type ProfileKind = 'principal' | 'secundario'
export type PlanTier = 'free' | 'plus' | 'premium'

export interface Profile {
  id: string
  user_id: string
  kind: ProfileKind
  plan_tier: PlanTier
  nome: string
  email: string
  telefone: string | null
  endereco: string | null
  avatar_url: string | null
}

export interface ProfileInput {
  nome: string
  email: string
  telefone?: string
  endereco?: string
}

export const profilesApi = {
  list: () => api.get<Profile[]>('/profiles'),
  create: (data: ProfileInput) => api.post<Profile>('/profiles', data),
  update: (id: string, data: ProfileInput) => api.put<Profile>(`/profiles/${id}`, data),
  delete: (id: string) => api.delete<{ msg: string }>(`/profiles/${id}`),
  activate: (id: string) => api.post<{ msg: string }>(`/profiles/${id}/activate`, {}),
  uploadAvatar: (id: string, file: File) => api.upload<{ avatar_url: string }>(`/profiles/${id}/avatar`, file),
}
