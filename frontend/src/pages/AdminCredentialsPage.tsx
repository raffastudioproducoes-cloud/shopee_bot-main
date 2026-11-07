import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { AdminAiCredentialCard } from '../components/credentials/AdminAiCredentialCard'
import { AdminShopeeCredentialCard } from '../components/credentials/AdminShopeeCredentialCard'
import { ApiError } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { credentialsApi, type AdminTestAllResult, type CredentialStatusWithLight } from '../api/credentials'
import { CREDENTIAL_BRAND_LOGOS } from '../lib/credentialPlatforms'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'

const NETWORKS = [
  { key: 'facebook', label: 'Facebook' },
  { key: 'instagram', label: 'Instagram' },
  { key: 'kwai', label: 'Kwai' },
  { key: 'threads', label: 'Threads' },
  { key: 'tiktok', label: 'TikTok' },
  { key: 'x', label: 'X (Twitter)' },
] as const

type Network = typeof NETWORKS[number]['key']
type NetworkStatus = Pick<CredentialStatusWithLight, 'connected' | 'light' | 'state' | 'status_text' | 'checked_at'>

function StatusCard({ network, label, status, result }: {
  network: Network; label: string; status?: NetworkStatus; result?: AdminTestAllResult['results'][string]
}) {
  const state = result?.state === 'skipped' ? status?.state : result?.state || status?.state
  const checkedAt = result?.checked_at || status?.checked_at
  const tone = state === 'ok' ? 'mint' : 'neutral'
  const image = CREDENTIAL_BRAND_LOGOS[network]?.[0]
  return (
    <div className="admin-credential-status-card" data-state={state || 'disconnected'}>
      <span className={`credential-brand credential-brand--${network}`} aria-hidden="true">
        {image && <img src={`/brand-logos/${image}`} alt="" />}
      </span>
      <div className="admin-credential-status-card__text">
        <strong>{label}</strong>
        {checkedAt && <small>Último teste: {new Date(checkedAt).toLocaleString('pt-BR')}</small>}
      </div>
      <Badge tone={tone}>{state === 'ok' ? 'Funcionando' : result?.state === 'error' ? result.status_text : status?.status_text || 'Desconectado'}</Badge>
    </div>
  )
}

export default function AdminCredentialsPage() {
  const [banner, setBanner] = useState<{ ok: boolean; text: string } | null>(null)
  const [lastBatch, setLastBatch] = useState<AdminTestAllResult | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logout = useAuthStore(state => state.logout)
  const onAuthError = (error: Error) => {
    if (error instanceof ApiError && error.status === 401) {
      logout()
      void navigate({ to: '/login' })
    } else {
      setBanner({ ok: false, text: error.message || 'Falha no diagnóstico.' })
    }
  }
  const { data: statuses, isLoading, error } = useQuery({
    queryKey: ['admin', 'credentials', 'status'],
    queryFn: () => credentialsApi.listAdminStatus(),
    refetchInterval: query => Object.values(query.state.data ?? {}).some(status => status.state === 'testing') ? 1500 : false,
  })
  const testAll = useMutation({
    mutationFn: () => credentialsApi.testAllAdminConnections(),
    onSuccess: (result) => {
      setLastBatch(result)
      setBanner({ ok: true, text: `${result.tested} conexão(ões) testada(s); ${result.skipped} sem credencial para testar.` })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'credentials', 'status'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'ai'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'shopee'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'recent-logs'] })
    },
    onError: onAuthError,
  })
  return (
    <div className="csp-s-0164">
      <div className="admin-diagnostic-page">
      <h1 className="csp-s-0165">Diagnóstico de credenciais</h1>
      <p className="csp-s-0166">IA e API Shopee atendem toda a plataforma. As conexões sociais abaixo pertencem ao perfil ADMIN ativo; IDs de afiliados são individuais por conta.</p>
      {banner && <p role="status" className={`admin-diagnostic-banner ${banner.ok ? 'is-success' : 'is-error'}`}>{banner.text}</p>}

      <div className="admin-platform-grid" aria-label="Credenciais globais da plataforma">
        <AdminAiCredentialCard setBanner={setBanner} onAuthError={onAuthError} />
        <AdminShopeeCredentialCard setBanner={setBanner} onAuthError={onAuthError} />
      </div>

      <Panel surface="dark" className="admin-diagnostic-results" padding={18}>
        <div className="admin-diagnostic-results__heading">
          <div>
            <h2 className="csp-s-0167">Estado das conexões</h2>
            <p>Verificação real das conexões configuradas. Plataformas sem credencial não são testadas.</p>
          </div>
          <Button type="button" variant="primary" loading={testAll.isPending} disabled={testAll.isPending || isLoading || Boolean(error)} onClick={() => testAll.mutate()}>
            {testAll.isPending ? 'Testando conexões…' : 'Testar todas as conexões'}
          </Button>
        </div>
        {isLoading ? <PageSkeleton variant="list" heading={false} count={2} /> : error ? (
          <p role="alert">Não foi possível consultar as conexões. Tente recarregar a página.</p>
        ) : (
          <div className="admin-connection-results" aria-live="polite">
            {NETWORKS.map(({ key, label }) => (
              <StatusCard key={key} network={key} label={label} status={statuses?.[key]}
                result={lastBatch?.results[key]} />
            ))}
          </div>
        )}
        {lastBatch && <p className="admin-diagnostic-results__footer" role="status">
          Último lote: {lastBatch.tested} verificadas, {lastBatch.skipped} ignoradas por ausência de credenciais.
          {' '}Eventos gerados no log do servidor e enviados à Central de Logs (quando o banco estiver disponível).
        </p>}
      </Panel>
      </div>
    </div>
  )
}
