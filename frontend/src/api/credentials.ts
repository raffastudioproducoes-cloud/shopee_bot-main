import { api } from '../lib/api'

export type SimpleNetwork = 'shopee' | 'x' | 'facebook' | 'instagram' | 'tiktok' | 'kwai'

export type ConnectionLight = 'green' | 'yellow' | 'red'

export interface CredentialStatus {
  connected: boolean
}

export interface CredentialStatusWithLight extends CredentialStatus {
  light: ConnectionLight
  /** disconnected | untested | expired | error | stale | ok | testing (GET /credentials). */
  state?: CredentialState
  /** Texto curto do estado, coerente com a luz (sem segredo). */
  status_text?: string
  checked_at: string | null
  check_message: string | null
  /** Só no X: a conexão tem a permissão media.write (imagens). Ausente nas outras redes. */
  supports_media?: boolean
  /** Só no X: escopos OAuth que faltam (ex.: ["media.write"]). */
  missing_scopes?: string[]
}

export type CredentialState = 'disconnected' | 'untested' | 'expired' | 'error' | 'stale' | 'ok' | 'testing'

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

  /** "Testar conexão" — qualquer usuário testa a PRÓPRIA credencial (backend escopa por user_id/perfil). */
  async testConnection(network: SimpleNetwork | 'threads'): Promise<TestConnectionResult> {
    return api.post<TestConnectionResult>(`/credentials/${network}/test`, undefined)
  },

}

// ── Chave de IA do próprio usuário/perfil (sem chave global no servidor) ──

export type AiProvider = 'gemini' | 'openai' | 'anthropic'

export const AI_PROVIDERS: { key: AiProvider; label: string; helpUrl: string }[] = [
  { key: 'gemini', label: 'Google Gemini', helpUrl: 'https://aistudio.google.com/apikey' },
  { key: 'openai', label: 'OpenAI', helpUrl: 'https://platform.openai.com/api-keys' },
  { key: 'anthropic', label: 'Anthropic (Claude)', helpUrl: 'https://platform.claude.com/docs/en/get-api-key' },
]

export interface AiProviderStatus extends CredentialStatusWithLight {
  model: string | null
  default_model: string
}

export interface AiCredentialsStatus {
  providers: Record<AiProvider, AiProviderStatus>
  /** Provedor usado pelo "Gerar texto com IA" (último salvo); null = sem chave. */
  active: AiProvider | null
}

export const aiCredentialsApi = {
  async list(): Promise<AiCredentialsStatus> {
    return api.get<AiCredentialsStatus>('/credentials/ai')
  },
  async save(provider: AiProvider, apiKey: string, model?: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>(`/credentials/ai/${provider}`, { api_key: apiKey, model: model || undefined })
  },
  async delete(provider: AiProvider): Promise<CredentialStatus> {
    return api.delete<CredentialStatus>(`/credentials/ai/${provider}`)
  },
  async test(provider: AiProvider): Promise<TestConnectionResult> {
    return api.post<TestConnectionResult>(`/credentials/ai/${provider}/test`, undefined)
  },
}
