import { api } from '../lib/api'
import type { CredentialStatus } from './credentials'

/** Endpoints de override manual. O módulo que consome esta API é carregado
 * somente depois da confirmação de ADMIN pelo backend. */
export const adminCredentialsApi = {
  saveThreads(tUserId: string, accessToken: string): Promise<CredentialStatus> {
    return api.put('/credentials/threads', { t_user_id: tUserId, access_token: accessToken })
  },

  saveX(accessToken: string, refreshToken?: string): Promise<CredentialStatus> {
    return api.put('/credentials/x/manual', {
      user_access_token: accessToken,
      user_refresh_token: refreshToken || undefined,
    })
  },

  saveFacebook(pageId: string, accessToken: string, pageName?: string): Promise<CredentialStatus> {
    return api.put('/credentials/facebook/manual', {
      page_id: pageId,
      page_access_token: accessToken,
      page_name: pageName || undefined,
    })
  },

  saveTikTok(openId: string, accessToken: string, refreshToken?: string): Promise<CredentialStatus> {
    return api.put('/credentials/tiktok/manual', {
      open_id: openId,
      user_access_token: accessToken,
      refresh_token: refreshToken || undefined,
    })
  },

  saveInstagram(igUserId: string, accessToken: string): Promise<CredentialStatus> {
    return api.put('/credentials/instagram/manual', {
      ig_user_id: igUserId,
      user_access_token: accessToken,
    })
  },

  saveKwai(appId: string, secret: string): Promise<CredentialStatus> {
    return api.put('/credentials/kwai', { app_id: appId, secret })
  },
}
