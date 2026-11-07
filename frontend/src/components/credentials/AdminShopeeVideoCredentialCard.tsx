import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminShopeeVideoApi } from '../../api/shopeeVideo'
import { Button } from '../ui/Button'
import { TextInput } from '../ui/TextInput'
import { StatusBadge } from '../ui/StatusBadge'
import { Icon } from '../ui/Icon'

type Banner = { ok: boolean; text: string } | null

export function AdminShopeeVideoCredentialCard({ setBanner, onAuthError }: {
  setBanner: (value: Banner) => void
  onAuthError: (error: Error) => void
}) {
  const [partnerId, setPartnerId] = useState('')
  const [partnerKey, setPartnerKey] = useState('')
  const [sandbox, setSandbox] = useState(true)
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'shopee-video'], queryFn: adminShopeeVideoApi.status,
  })
  const save = useMutation({
    mutationFn: () => adminShopeeVideoApi.save(Number(partnerId), partnerKey, sandbox),
    onSuccess: () => {
      setPartnerId(''); setPartnerKey('')
      setBanner({ ok: true, text: 'Configuração Shopee Vídeo salva. Nenhuma publicação foi ativada.' })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'shopee-video'] })
      void queryClient.invalidateQueries({ queryKey: ['shopee-video', 'status'] })
    },
    onError: onAuthError,
  })
  return (
    <details className="admin-platform-card">
      <summary className="admin-platform-card__header csp-s-0192">
        <span className="credential-brand credential-brand--shopee-video" aria-hidden="true">
          <img src="/brand-logos/shopee.svg" alt="" />
        </span>
        <span className="admin-platform-card__heading">
          <h2>Shopee Vídeo</h2><small>Open Platform · criadores afiliados</small>
        </span>
        <StatusBadge tone={data?.configured ? 'positive' : 'neutral'}>
          {data?.configured ? 'Chave salva' : 'Não configurada'}
        </StatusBadge>
        <Icon name="chevron-down" size={18} className="admin-platform-card__chevron" />
      </summary>
      <div className="admin-platform-card__body">
        <p>Use o <strong>Partner ID e a Partner Key da aplicação Shopee Video Management</strong>.
          Eles são diferentes da chave da API Shopee Afiliados. A chave fica cifrada no servidor.</p>
        {isLoading ? <p role="status">Consultando configuração…</p> : isError ? (
          <div role="alert">Não foi possível consultar a configuração.
            <Button type="button" variant="ghost" onClick={() => void refetch()}>Tentar novamente</Button>
          </div>
        ) : (
          <form className="csp-s-0210" onSubmit={event => { event.preventDefault(); save.mutate() }}>
            <div className="csp-named-field-grid">
              <TextInput label="Partner ID" inputMode="numeric" value={partnerId}
                onChange={event => setPartnerId(event.target.value)} required autoComplete="off"
                placeholder={data?.partner_id ? `Atual: ${data.partner_id}` : 'Partner ID'} />
              <TextInput label="Partner Key" type="password" value={partnerKey}
                onChange={event => setPartnerKey(event.target.value)} required autoComplete="off"
                placeholder={data?.configured ? 'Salva — informe somente para trocar' : 'Partner Key'} />
            </div>
            <label className="csp-s-0211">
              <input type="checkbox" checked={sandbox} onChange={e => setSandbox(e.target.checked)} />{' '}
              Usar ambiente de testes da Shopee (sandbox)
            </label>
            <p role="note">Callback: {data?.callback_configured ? 'configurado no servidor' : 'pendente no servidor'}.
              A publicação de vídeos reais permanece desligada.</p>
            <div className="csp-s-0213">
              <Button type="submit" variant="primary" loading={save.isPending}
                disabled={save.isPending || !/^\d+$/.test(partnerId) || partnerKey.trim().length < 8}>
                {save.isPending ? 'Salvando…' : 'Salvar configuração'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </details>
  )
}
