import { api, ApiError } from '../lib/api'

export type SimpleNetwork = 'shopee' | 'x' | 'facebook' | 'instagram' | 'tiktok' | 'kwai'

export interface CredentialStatus {
  connected: boolean
}

export type CredentialsStatusMap = Record<SimpleNetwork | 'threads', CredentialStatus>

export const credentialsApi = {
  async list(): Promise<CredentialsStatusMap> {
    return api.get<CredentialsStatusMap>('/credentials')
  },

  async save(network: SimpleNetwork, appId: string, secret: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>(`/credentials/${network}`, { app_id: appId, secret })
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
}

export { ApiError }
