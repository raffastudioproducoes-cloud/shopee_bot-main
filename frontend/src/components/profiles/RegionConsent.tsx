import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi } from '../../api/profiles'
import { Panel } from '../ui/Panel'
import { Button } from '../ui/Button'

const regions = [
  ['BR-RJ','Brasil — Rio de Janeiro'],['BR-SP','Brasil — São Paulo'],
  ['BR-MG','Brasil — Minas Gerais'],['BR-BA','Brasil — Bahia'],
  ['BR-OTHER','Brasil — Outra UF'],['PT','Portugal'],['US','Estados Unidos'],
  ['GB','Reino Unido'],['DE','Alemanha'],['JP','Japão'],
  ['AU','Austrália'],['OTHER','Outro país'],
] as const

export function RegionConsent() {
  const client = useQueryClient()
  const {data, isLoading, isError} = useQuery({queryKey:['region-preference'],queryFn:profilesApi.getRegionPreference})
  const [region,setRegion] = useState('')
  const [agreed,setAgreed] = useState(false)
  const save = useMutation({mutationFn:profilesApi.saveRegionPreference,onSuccess:()=>{
    void client.invalidateQueries({queryKey:['region-preference']})
    void client.invalidateQueries({queryKey:['admin','metrics']})
    setAgreed(false)
  }})
  const revoke = useMutation({mutationFn:profilesApi.deleteRegionPreference,onSuccess:()=>{
    void client.invalidateQueries({queryKey:['region-preference']})
    void client.invalidateQueries({queryKey:['admin','metrics']})
    setRegion('')
    setAgreed(false)
  }})
  return <Panel style={{padding:20}}>
    <h2 style={{marginTop:0}}>Região aproximada (opcional)</h2>
    <p>Você pode contribuir voluntariamente para estatísticas regionais do Auto Orbital. Apenas país/UF será salvo, nunca endereço, GPS ou IP para este mapa. Uma região só aparece no mapa administrativo se pelo menos três contas tiverem optado por ela.</p>
    {isLoading ? <p>Consultando preferência...</p> : isError ? <p role="alert">Não foi possível consultar a preferência.</p> : <>
      {data?.consented && <p role="status">Participação ativa: {regions.find(r=>r[0]===data.region)?.[1]??'Região escolhida'}. Você pode retirar seu consentimento a qualquer momento.</p>}
      <label htmlFor="account-region">País / região</label>
      <select id="account-region" value={region || data?.region || ''} onChange={e=>{setRegion(e.target.value);setAgreed(false)}} style={{display:'block',padding:10,maxWidth:'100%',margin:'8px 0 14px'}}>
        <option value="">Selecione uma região</option>
        {regions.map(([code,label])=><option key={code} value={code}>{label}</option>)}
      </select>
      <label style={{display:'flex',gap:10,alignItems:'flex-start',marginBottom:14}}>
        <input type="checkbox" checked={agreed} onChange={e=>setAgreed(e.target.checked)}/>
        Autorizo o uso da minha região aproximada em estatísticas agregadas, podendo retirar essa autorização quando quiser.
      </label>
      <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
        <Button disabled={!agreed || !(region||data?.region) || save.isPending} onClick={()=>save.mutate(region||data!.region!)}>Salvar preferência</Button>
        {data?.consented && <Button variant="secondary" disabled={revoke.isPending} onClick={()=>revoke.mutate()}>Retirar consentimento</Button>}
      </div>
      {(save.isError||revoke.isError)&&<p role="alert">Não foi possível salvar a preferência. Tente novamente.</p>}
    </>}
    <p style={{fontSize:12,opacity:.75}}>Regiões com menos de três participantes ficam ocultas. A retirada do consentimento exclui o registro regional; não há geolocalização automática.</p>
  </Panel>
}
