import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminShopeeApi } from '../../api/credentials'
import { Button } from '../ui/Button'
import { TextInput } from '../ui/TextInput'
import { StatusBadge } from '../ui/StatusBadge'
import { Icon } from '../ui/Icon'

type Banner = { ok: boolean; text: string } | null

/** Apenas no painel ADMIN; a resposta da API nunca contém o Secret. */
export function AdminShopeeCredentialCard({
  setBanner, onAuthError,
}: {
  setBanner: (value: Banner) => void
  onAuthError: (error: Error) => void
}) {
  const [appId, setAppId] = useState('')
  const [secret, setSecret] = useState('')
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'shopee'],
    queryFn: adminShopeeApi.status,
  })
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'shopee'] })
    void queryClient.invalidateQueries({ queryKey: ['shopee', 'affiliate'] })
  }
  const save = useMutation({
    mutationFn: () => adminShopeeApi.save(appId, secret),
    onSuccess: () => {
      setAppId('')
      setSecret('')
      setBanner({ ok: true, text: 'API Shopee global salva. Use “Testar todas as conexões” no diagnóstico.' })
      refresh()
    },
    onError: onAuthError,
  })
  const remove = useMutation({
    mutationFn: adminShopeeApi.delete,
    onSuccess: () => { setBanner({ ok: true, text: 'API Shopee global desconectada.' }); refresh() },
    onError: onAuthError,
  })
  return (
    <details className="admin-platform-card">
      <summary className="admin-platform-card__header csp-s-0192">
        <span className="credential-brand credential-brand--shopee" aria-hidden="true">
          <img src="/brand-logos/shopee.svg" alt="" />
        </span>
        <span className="admin-platform-card__heading">
          <h2 className="csp-s-0194">Shopee Afiliados</h2>
          <small>API da plataforma</small>
        </span>
        <StatusBadge tone={data?.state === 'ok' ? 'positive' : 'neutral'}>
          {data?.connected ? data.state === 'ok' ? 'API testada' : 'API salva (teste pendente)' : 'Não configurada'}
        </StatusBadge>
        <Icon name="chevron-down" size={18} className="admin-platform-card__chevron" />
      </summary>
      <div className="admin-platform-card__body">
      <p className="csp-s-0211">
        Seu App ID e Secret consultam o catálogo para todos os usuários. Cada cliente cadastra
        separadamente o próprio ID de afiliado; o sistema não publica seu link pessoal no lugar do cliente.
      </p>
      {isLoading ? <p role="status">Carregando API Shopee…</p> : isError ? (
        <div role="alert">Falha ao consultar API Shopee.
          <Button type="button" variant="ghost" onClick={() => { void refetch() }}>Tentar novamente</Button>
        </div>
      ) : (
        <form className="csp-s-0210" onSubmit={event => { event.preventDefault(); save.mutate() }}>
          <div className="csp-named-field-grid">
            <TextInput label="App ID" value={appId} onChange={event => setAppId(event.target.value)}
              autoComplete="off" required placeholder={data?.connected ? 'Salvo — informe outro para trocar' : 'App ID'} />
            <TextInput label="App Secret" value={secret} type="password" onChange={event => setSecret(event.target.value)}
              autoComplete="off" required placeholder={data?.connected ? 'Salvo — informe outro para trocar' : 'Secret'} />
          </div>
          <div className="csp-s-0213">
            {data?.connected && <>
              <Button type="button" variant="ghost" disabled={remove.isPending} onClick={() => remove.mutate()}>
                {remove.isPending ? 'Desconectando…' : 'Desconectar'}
              </Button>
            </>}
            <Button type="submit" variant="primary" disabled={save.isPending || !appId.trim() || !secret.trim()}>
              {save.isPending ? 'Salvando…' : 'Salvar credenciais'}
            </Button>
          </div>
        </form>
      )}
      </div>
    </details>
  )
}
