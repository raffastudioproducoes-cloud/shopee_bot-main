import { formatInstant } from '../../lib/userTimeZone'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi } from '../../api/profiles'
import { useAuthStore } from '../../stores/authStore'
import { Panel } from '../ui/Panel'
import { Button } from '../ui/Button'

const regions = [
  ['BR-RJ', 'Brasil — Rio de Janeiro'], ['BR-SP', 'Brasil — São Paulo'],
  ['BR-MG', 'Brasil — Minas Gerais'], ['BR-BA', 'Brasil — Bahia'],
  ['BR-OTHER', 'Brasil — Outra UF'], ['PT', 'Portugal'], ['US', 'Estados Unidos'],
  ['GB', 'Reino Unido'], ['DE', 'Alemanha'], ['JP', 'Japão'],
  ['AU', 'Austrália'], ['OTHER', 'Outro país'],
] as const

/** Região declarada é independente do ponto de GPS; não faz nova consulta ao dispositivo. */
export function RegionConsent() {
  const client = useQueryClient()
  const userId = useAuthStore(s => s.user?.id)
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['region-preference', userId],
    queryFn: profilesApi.getRegionPreference,
    enabled: Boolean(userId),
    retry: 1,
  })
  const { data: location, isError: locationError } = useQuery({
    queryKey: ['location-sharing', userId],
    queryFn: profilesApi.getLocationSharing,
    enabled: Boolean(userId),
    retry: 1,
  })
  const [region, setRegion] = useState('')
  const [agreed, setAgreed] = useState(false)
  const revokeLocation = useMutation({
    mutationFn: () => profilesApi.setLocationSharing({ choice: 'revoked' }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['location-sharing'] })
      void client.invalidateQueries({ queryKey: ['admin', 'location-points'] })
    },
  })
  const save = useMutation({
    mutationFn: profilesApi.saveRegionPreference,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['region-preference'] })
      void client.invalidateQueries({ queryKey: ['admin', 'metrics'] })
      setAgreed(false)
    },
  })
  const revoke = useMutation({
    mutationFn: profilesApi.deleteRegionPreference,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['region-preference'] })
      void client.invalidateQueries({ queryKey: ['admin', 'metrics'] })
      setRegion('')
      setAgreed(false)
    },
  })

  const chosenRegion = region || data?.region || ''
  const locationStatus = location?.choice === 'accepted' ? 'Autorizada'
    : location?.choice === 'declined' ? 'Recusada'
    : location?.choice === 'revoked' ? 'Autorização retirada; ponto excluído'
    : 'Não registrada'

  return (
    <Panel style={{ padding: 20 }}>
      <h3 className="csp-s-0101">GPS — coleta pontual</h3>
      <p>Localização aproximada: <strong>{locationError ? 'Consulta indisponível' : locationStatus}</strong>.</p>
      {location?.choice === 'accepted' && (
        <div className="csp-s-0102">
          <p>Uma posição aproximada foi registrada em {location.collected_at
            ? formatInstant(location.collected_at)
            : 'data não disponível'}. O administrador pode visualizar esse ponto para planejar a expansão do serviço.</p>
          <Button variant="secondary" disabled={revokeLocation.isPending} onClick={() => revokeLocation.mutate()}>
            Excluir localização e retirar autorização
          </Button>
        </div>
      )}
      {revokeLocation.isError && <p role="alert">Não foi possível excluir a localização. Tente novamente.</p>}
      <p className="csp-s-0103">
        O navegador só é consultado uma vez no primeiro acesso, após sua escolha no aviso.
        Não fazemos novas consultas de GPS, mesmo após uma revogação. A opção de região abaixo é manual.
      </p>
      <h3>Minha região (opcional e independente do GPS)</h3>
      <p>Você pode informar país/UF sem usar GPS. A região declarada participa apenas de estatísticas agregadas quando pelo menos três contas informam a mesma região.</p>
      {isLoading && <p role="status">Consultando preferência salva...</p>}
      {isError && <p role="alert">Não foi possível consultar a região. <button type="button" onClick={() => { void refetch() }}>Tentar novamente</button></p>}
      {data?.consented && <p role="status">Região cadastrada: {regions.find(r => r[0] === data.region)?.[1] ?? 'Região escolhida'}.</p>}
      <label htmlFor="account-region" className="csp-s-0104">País / região</label>
      <select id="account-region" value={chosenRegion} onChange={e => { setRegion(e.target.value); setAgreed(false) }}
        className="csp-s-0105">
        <option value="">Selecione uma região</option>
        {regions.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
      </select>
      <label className="csp-s-0106">
        <input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} />
        Autorizo o uso da região declarada em estatísticas agregadas, podendo excluí-la quando quiser.
      </label>
      <div className="csp-s-0107">
        <Button disabled={!agreed || !chosenRegion || save.isPending} onClick={() => save.mutate(chosenRegion)}>
          {save.isPending ? 'Salvando...' : 'Salvar região'}
        </Button>
        {data?.consented && (
          <Button variant="secondary" disabled={revoke.isPending} onClick={() => revoke.mutate()}>Excluir região</Button>
        )}
      </div>
      {(save.isError || revoke.isError) && <p role="alert">Não foi possível salvar a preferência. Tente novamente.</p>}
    </Panel>
  )
}
