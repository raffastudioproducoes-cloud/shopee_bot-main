import { formatInstant } from '../lib/userTimeZone'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { AdminAiCredentialCard } from '../components/credentials/AdminAiCredentialCard'
import { AdminShopeeCredentialCard } from '../components/credentials/AdminShopeeCredentialCard'
import { AdminShopeeVideoCredentialCard } from '../components/credentials/AdminShopeeVideoCredentialCard'
import { ApiError } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { credentialsApi, type AdminTestAllResult, type CredentialStatusWithLight, type SimpleNetwork } from '../api/credentials'
import { buildAdminDiagnosticSections, CREDENTIAL_BRAND_LOGOS, type AdminDiagnosticPlatform } from '../lib/credentialPlatforms'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Button } from '../components/ui/Button'

const CATALOG = buildAdminDiagnosticSections()
type NetworkStatus = Pick<CredentialStatusWithLight, 'connected' | 'light' | 'state' | 'status_text' | 'checked_at'>

function StatusCard({ platform, status, result }: {
  platform: AdminDiagnosticPlatform; status?: NetworkStatus; result?: AdminTestAllResult['results'][string]
}) {
  const planned = platform.availability === 'planned'
  const state = planned ? 'planned' : result?.state === 'skipped' ? status?.state : result?.state || status?.state
  const checkedAt = planned ? null : result?.checked_at || status?.checked_at
  const tone = state === 'ok' ? 'mint' : 'neutral'
  const images = CREDENTIAL_BRAND_LOGOS[platform.key] ?? []
  const plannedLabel = platform.key === 'shopee-video' ? 'OAuth em homologação' : 'Em breve'
  return (
    <div className="admin-credential-status-card" data-state={state || 'disconnected'}>
      <span className={`credential-brand credential-brand--${platform.key}`} aria-hidden="true">
        {images.map(image => <img key={image} src={`/brand-logos/${image}`} alt="" loading="lazy" />)}
      </span>
      <div className="admin-credential-status-card__text">
        <strong>{platform.title}</strong>
        {checkedAt && <small>Último teste: {formatInstant(checkedAt)}</small>}
      </div>
      <Badge tone={tone}>{planned ? plannedLabel : state === 'ok' ? 'Funcionando' : result?.state === 'error' ? result.status_text : status?.status_text || 'Desconectado'}</Badge>
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
      const failed = Object.values(result.results).filter(item => item.state === 'error').length
      setBanner({
        ok: failed === 0,
        text: `${result.tested} conexão(ões) testada(s); ${failed} falha(s); ${result.skipped} sem credencial para testar.`,
      })
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
        <AdminShopeeVideoCredentialCard setBanner={setBanner} onAuthError={onAuthError} />
      </div>

      <Panel surface="dark" className="admin-diagnostic-results" padding={18}>
        <div className="admin-diagnostic-results__heading">
          <div>
            <h2 className="csp-s-0167">Estado das conexões</h2>
            <p>Verificação real das conexões configuradas. Plataformas “Em breve” são informativas e não participam dos testes.</p>
          </div>
          <Button type="button" variant="primary" loading={testAll.isPending} disabled={testAll.isPending || isLoading || Boolean(error)} onClick={() => testAll.mutate()}>
            {testAll.isPending ? 'Testando conexões…' : 'Testar todas as conexões'}
          </Button>
        </div>
        {isLoading ? <PageSkeleton variant="list" heading={false} count={2} /> : error ? (
          <p role="alert">Não foi possível consultar as conexões. Tente recarregar a página.</p>
        ) : (
          <div className="admin-diagnostic-catalog" aria-live="polite">
            <section className="admin-diagnostic-section" aria-labelledby="admin-stores-title">
              <h3 id="admin-stores-title">Lojas <small>{CATALOG.stores.length} integrações planejadas</small></h3>
              <div className="admin-connection-results">
                {CATALOG.stores.map(platform => <StatusCard key={platform.key} platform={platform} />)}
              </div>
            </section>
            <section className="admin-diagnostic-section" aria-labelledby="admin-social-title">
              <h3 id="admin-social-title">Redes sociais <small>{CATALOG.social.length} plataformas</small></h3>
              <div className="admin-connection-results">
                {CATALOG.social.map(platform => (
                  <StatusCard key={platform.key} platform={platform}
                    status={platform.availability === 'active' ? statuses?.[platform.key as SimpleNetwork | 'threads'] : undefined}
                    result={platform.availability === 'active' ? lastBatch?.results[platform.key] : undefined} />
                ))}
              </div>
            </section>
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
