import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi } from '../../api/profiles'
import { useAuthStore } from '../../stores/authStore'
import { Panel } from '../ui/Panel'
import { Button } from '../ui/Button'

const options = [
  ['search','Busca na internet'], ['social','Redes sociais'],
  ['referral','Indicação de outra pessoa'], ['direct','Já conhecia o endereço do site'],
  ['other','Outro meio'],
] as const

export function AcquisitionConsent() {
  const client = useQueryClient()
  const userId = useAuthStore(s => s.user?.id)
  const { data, isLoading, isError, refetch } = useQuery({queryKey:['acquisition-source', userId], queryFn:profilesApi.getAcquisitionSource, enabled:Boolean(userId), retry:1})
  const [source,setSource] = useState('')
  const [confirmed,setConfirmed] = useState(false)
  const save=useMutation({mutationFn:profilesApi.saveAcquisitionSource,onSuccess:()=>{
    void client.invalidateQueries({queryKey:['acquisition-source']})
    void client.invalidateQueries({queryKey:['admin','operations']})
    setConfirmed(false)
  }})
  const revoke=useMutation({mutationFn:profilesApi.deleteAcquisitionSource,onSuccess:()=>{
    void client.invalidateQueries({queryKey:['acquisition-source']})
    void client.invalidateQueries({queryKey:['admin','operations']})
    setSource('')
    setConfirmed(false)
  }})
  return <Panel style={{padding:20}}>
    <h2 className="csp-s-0067">Como conheceu o Auto Orbital? (opcional)</h2>
    <p>Ajude-nos a entender quais canais apresentam o Auto Orbital a novos usuários. Esta informação é declarada por você, sem rastrear sua navegação. Somente grupos com pelo menos três respostas aparecem no painel administrativo.</p>
    {isLoading && <p role="status">Consultando resposta salva...</p>}
    {isError && <p role="alert">Não foi possível consultar sua resposta anterior. Você ainda pode escolher uma opção abaixo e salvá-la. <button type="button" onClick={() => { void refetch() }}>Tentar consultar novamente</button></p>}
    <>
      {data?.declared && <p role="status">Origem informada: {options.find(item=>item[0]===data.source)?.[1]??'Outra'}</p>}
      <label htmlFor="acquisition-source-choice" className="csp-s-0068">Como você conheceu o Auto Orbital?</label>
      <select id="acquisition-source-choice" value={source||data?.source||''} onChange={e=>{setSource(e.target.value);setConfirmed(false)}} className="csp-s-0069">
        <option value="">Selecione</option>
        {options.map(([code,label])=><option key={code} value={code}>{label}</option>)}
      </select>
      <label className="csp-s-0070">
        <input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>
        Concordo em compartilhar essa informação em estatísticas agregadas e sei que posso excluí-la.
      </label>
      <div className="csp-s-0071">
        <Button disabled={!confirmed||!(source||data?.source)||save.isPending} onClick={()=>save.mutate(source||data!.source!)}>{save.isPending ? 'Salvando...' : 'Salvar minha resposta'}</Button>
        {data?.declared && <Button variant="secondary" disabled={revoke.isPending} onClick={()=>revoke.mutate()}>Excluir resposta</Button>}
      </div>
      {(save.isError||revoke.isError)&&<p role="alert">Falha ao registrar preferência. Tente novamente.</p>}
    </>
  </Panel>
}
