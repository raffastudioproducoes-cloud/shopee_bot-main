import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { AdminOverrides } from '../components/credentials/AdminOverrides'
import { ApiError } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { credentialsApi } from '../api/credentials'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { PageSkeleton } from '../components/ui/Skeleton'

export default function AdminCredentialsPage() {
  const [banner, setBanner] = useState<{ ok: boolean; text: string } | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logout = useAuthStore(state => state.logout)
  const { data: statuses, isLoading, error } = useQuery({
    queryKey: ['admin', 'credentials', 'status'],
    queryFn: () => credentialsApi.listAdminStatus(),
    refetchInterval: query => Object.values(query.state.data ?? {}).some(status => status.state === 'testing') ? 1500 : false,
  })
  return (
    <div className="csp-s-0164">
      <h1 className="csp-s-0165">Diagnóstico de credenciais</h1>
      <p className="csp-s-0166">As alterações pertencem ao seu perfil ativo.</p>
      {banner && <p role="status" style={{ color: banner.ok ? 'var(--positive-ink)' : 'var(--negative-ink)' }}>{banner.text}</p>}
      {isLoading ? <PageSkeleton variant="list" heading={false} count={1} /> : error ? <p role="alert">Não foi possível acompanhar o teste de conexão.</p> : (
        <Panel surface="dark" style={{ padding: 16 }}>
          <h2 className="csp-s-0167">Resultado das conexões</h2>
          <div className="admin-connection-results" aria-live="polite">
            {Object.entries(statuses ?? {}).map(([network, status]) => <div key={network}><strong>{network}</strong><Badge tone={status.state === 'ok' ? 'mint' : 'neutral'}>{status.status_text || status.state || 'Desconectado'}</Badge></div>)}
          </div>
        </Panel>
      )}
      <AdminOverrides
        setBanner={value => setBanner(value?.ok ? { ok: true, text: 'Credencial salva. Acompanhe o resultado em “Resultado das conexões”.' } : value)}
        onSaved={() => { void queryClient.invalidateQueries({ queryKey: ['admin', 'credentials', 'status'] }) }}
        onAuthError={error => {
          if (error instanceof ApiError && error.status === 401) {
            logout()
            void navigate({ to: '/login' })
          } else {
            setBanner({ ok: false, text: error.message || 'Erro ao salvar credencial.' })
          }
        }}
      />
    </div>
  )
}
