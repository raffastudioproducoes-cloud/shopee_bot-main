import { api, ApiError } from '../lib/api'

export type SimpleNetwork = 'shopee' | 'x' | 'facebook' | 'instagram' | 'tiktok' | 'kwai'

/** Link externo pra onde o usuário vai buscar/gerar a própria credencial —
 * só existe pra redes sem tela de login OAuth (Shopee: API de afiliados
 * não tem "Login with Shopee", só App ID/Secret gerado no portal deles). */
export const CREDENTIAL_HELP_LINKS: Partial<Record<SimpleNetwork, string>> = {
  shopee: 'https://affiliate.shopee.com.br/',
}

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

  async save(network: SimpleNetwork, appId: string, secret: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>(`/credentials/${network}`, {
      app_id: appId,
      secret,
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

  async authorizeX(): Promise<{ url: string }> {
    return api.get<{ url: string }>('/credentials/x/authorize')
  },

  async authorizeFacebook(): Promise<{ url: string }> {
    return api.get<{ url: string }>('/credentials/facebook/authorize')
  },

  /** "Testar conexão" — admin-only no backend (403 pra quem não é ADMIN). */
  async testConnection(network: SimpleNetwork | 'threads'): Promise<TestConnectionResult> {
    return api.post<TestConnectionResult>(`/credentials/${network}/test`, undefined)
  },
}

export { ApiError }
