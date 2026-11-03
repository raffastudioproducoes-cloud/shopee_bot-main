import { api } from '../lib/api'

export type ProfileKind = 'principal' | 'secundario'
export type PlanTier = 'free' | 'pro' | 'plus' | 'premium'

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

export interface ProfileQuota {
  tier: 'free' | 'pro' | 'premium'
  used: number
  limit: number | null
  unlimited: boolean
}

export const profilesApi = {
  quota: () => api.get<ProfileQuota>('/profiles/quota'),
  list: () => api.get<Profile[]>('/profiles'),
  create: (data: ProfileInput) => api.post<Profile>('/profiles', data),
  update: (id: string, data: ProfileInput) => api.put<Profile>(`/profiles/${id}`, data),
  delete: (id: string) => api.delete<{ msg: string }>(`/profiles/${id}`),
  activate: (id: string) => api.post<{ msg: string }>(`/profiles/${id}/activate`, {}),
  uploadAvatar: (id: string, file: File) => api.upload<{ avatar_url: string }>(`/profiles/${id}/avatar`, file),
  getLocationSharing: () => api.get<{choice:'pending'|'accepted'|'declined'|'revoked';latitude:number|null;longitude:number|null;collected_at:string|null}>('/profiles/location-sharing'),
  setLocationSharing: (data: {choice:'accepted'|'declined'|'revoked';latitude?:number;longitude?:number;accuracy_m?:number}) => api.put<{choice:string}>('/profiles/location-sharing',data),
  getGpsPreference: () => api.get<{enabled: boolean}>('/profiles/gps-preference'),
  setGpsPreference: (enabled: boolean) => api.put<{enabled: boolean}>('/profiles/gps-preference', {enabled}),
  getRegionPreference: () => api.get<{ region: string | null; consented: boolean }>('/profiles/region-preference'),
  saveRegionPreference: (region: string) => api.put<{region: string; consented: boolean}>('/profiles/region-preference', {region, consent: true}),
  deleteRegionPreference: () => api.delete<{region: null; consented: boolean}>('/profiles/region-preference'),
  getAcquisitionSource: () => api.get<{source: string | null; declared: boolean}>('/profiles/acquisition-source'),
  saveAcquisitionSource: (source: string) => api.put<{source: string; declared: boolean}>('/profiles/acquisition-source', {source, consent: true}),
  deleteAcquisitionSource: () => api.delete<{source: null; declared: boolean}>('/profiles/acquisition-source'),
}
