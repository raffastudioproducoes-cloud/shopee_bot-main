import { api, ApiError } from '../lib/api'

export type SimpleNetwork = 'shopee' | 'x' | 'facebook' | 'instagram' | 'tiktok' | 'kwai'

export type ConnectionLight = 'green' | 'yellow' | 'red'

export interface CredentialStatus {
  connected: boolean
}

export interface CredentialStatusWithLight extends CredentialStatus {
  light: ConnectionLight
  checked_at: string | null
  check_message: string | null
}

export type CredentialsStatusMap = Record<SimpleNetwork | 'threads', CredentialStatusWithLight>

export interface TestConnectionResult {
  light: ConnectionLight
  message: string
  checked_at: string
}

export const credentialsApi = {
  async list(): Promise<CredentialsStatusMap> {
    return api.get<CredentialsStatusMap>('/credentials')
  },

  async save(
    network: SimpleNetwork,
    appId: string,
    secret: string,
    pageId?: string,
  ): Promise<CredentialStatus> {
    // page_id só é relevante pro Facebook (Graph API precisa saber em
    // qual Página publicar) — as outras redes ignoram o campo.
    return api.put<CredentialStatus>(`/credentials/${network}`, {
      app_id: appId,
      secret,
      ...(network === 'facebook' ? { page_id: pageId } : {}),
    })
  },

  async delete(network: SimpleNetwork): Promise<CredentialStatus> {
    return api.delete<CredentialStatus>(`/credentials/${network}`)
  },

  async saveThreads(tUserId: string, accessToken: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>('/credentials/threads', {
      t_user_id: tUserId,
      access_token: accessToken,
    })
  },

  async deleteThreads(): Promise<CredentialStatus> {
    return api.delete<CredentialStatus>('/credentials/threads')
  },

  async authorizeThreads(): Promise<{ url: string }> {
    return api.get<{ url: string }>('/credentials/threads/authorize')
  },

  async authorizeTiktok(): Promise<{ url: string }> {
    return api.get<{ url: string }>('/credentials/tiktok/authorize')
  },

  async authorizeInstagram(): Promise<{ url: string }> {
    return api.get<{ url: string }>('/credentials/instagram/authorize')
  },

  /** "Testar conexão" — admin-only no backend (403 pra quem não é ADMIN). */
  async testConnection(network: SimpleNetwork | 'threads'): Promise<TestConnectionResult> {
    return api.post<TestConnectionResult>(`/credentials/${network}/test`, undefined)
  },
}

export { ApiError }
