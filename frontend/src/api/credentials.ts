import { api } from '../lib/api'

export type SimpleNetwork = 'shopee' | 'x' | 'facebook' | 'instagram' | 'tiktok' | 'kwai'

/** Link externo pra onde a credencial/app de cada rede é gerenciado.
 * Pra Shopee/Kwai (sem OAuth) é pra onde TODO usuário precisa ir pra pegar
 * o App ID/Secret que cola no formulário. Pras redes de app único
 * (Threads/X/Facebook/TikTok/Instagram) é só referência pro admin — quem
 * clica "Conectar" nunca precisa desse link, só quem administra o app da
 * plataforma (ver SIMPLE_NETWORKS/OAUTH_NETWORKS em api/routers/credentials.py).
 * URLs pras redes de app único replicam web/templates/panel/credentials.html
 * (mesma escolha já feita pro painel Flask legado) onde fazia sentido manter
 * consistência, e usam o domínio pedido por Rafa (developer.x.com) onde não. */
export const CREDENTIAL_HELP_LINKS: Partial<Record<SimpleNetwork | 'threads', string>> = {
  shopee: 'https://affiliate.shopee.com.br/',
  kwai: 'https://developer.kwai.com/',
  threads: 'https://developers.facebook.com/docs/threads',
  x: 'https://developer.x.com/',
  facebook: 'https://developers.facebook.com/',
  instagram: 'https://developers.facebook.com/',
  tiktok: 'https://developers.tiktok.com/',
}

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

  /** "Testar conexão" — qualquer usuário testa a PRÓPRIA credencial (backend escopa por user_id/perfil). */
  async testConnection(network: SimpleNetwork | 'threads'): Promise<TestConnectionResult> {
    return api.post<TestConnectionResult>(`/credentials/${network}/test`, undefined)
  },

  // Overrides manuais admin-only (colar token direto, bypassando OAuth —
  // debug/emergência). 403 pra quem não é ADMIN, mesmo padrão de
  // testConnection acima. Só os campos que existem de verdade na tabela de
  // cada rede (ver api/routers/credentials.py).
  async saveXManual(userAccessToken: string, userRefreshToken?: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>('/credentials/x/manual', {
      user_access_token: userAccessToken,
      user_refresh_token: userRefreshToken || undefined,
    })
  },

  async saveFacebookManual(pageId: string, pageAccessToken: string, pageName?: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>('/credentials/facebook/manual', {
      page_id: pageId,
      page_access_token: pageAccessToken,
      page_name: pageName || undefined,
    })
  },

  async saveTiktokManual(openId: string, userAccessToken: string, refreshToken?: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>('/credentials/tiktok/manual', {
      open_id: openId,
      user_access_token: userAccessToken,
      refresh_token: refreshToken || undefined,
    })
  },

  async saveInstagramManual(igUserId: string, userAccessToken: string): Promise<CredentialStatus> {
    return api.put<CredentialStatus>('/credentials/instagram/manual', {
      ig_user_id: igUserId,
      user_access_token: userAccessToken,
    })
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
