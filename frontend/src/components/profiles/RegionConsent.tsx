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

function regionFromPoint(lat: number, lon: number): string {
  if (lat > -24 && lat < -20 && lon > -45 && lon < -40) return 'BR-RJ'
  if (lat > -26 && lat < -19 && lon > -54 && lon < -44) return 'BR-SP'
  if (lat > -23 && lat < -14 && lon > -51 && lon < -39) return 'BR-MG'
  if (lat > -19 && lat < -8 && lon > -47 && lon < -37) return 'BR-BA'
  if (lat > -34 && lat < 6 && lon > -74 && lon < -34) return 'BR-OTHER'
  if (lat > 36 && lat < 43 && lon > -10 && lon < -6) return 'PT'
  if (lat > 24 && lat < 50 && lon > -126 && lon < -66) return 'US'
  if (lat > 49 && lat < 60 && lon > -9 && lon < 3) return 'GB'
  if (lat > 47 && lat < 56 && lon > 5 && lon < 16) return 'DE'
  if (lat > 24 && lat < 46 && lon > 123 && lon < 146) return 'JP'
  if (lat > -45 && lat < -10 && lon > 112 && lon < 154) return 'AU'
  return 'OTHER'
}
export function RegionConsent() {
  const client = useQueryClient()
  const {data, isLoading, isError} = useQuery({queryKey:['region-preference'],queryFn:profilesApi.getRegionPreference})
  const [region,setRegion] = useState('')
  const [agreed,setAgreed] = useState(false)
  const [gpsNote,setGpsNote] = useState('')
  const [gpsBusy,setGpsBusy] = useState(false)
  const {data:gps} = useQuery({queryKey:['gps-preference'],queryFn:profilesApi.getGpsPreference})
  const gpsMutation = useMutation({mutationFn:profilesApi.setGpsPreference,onSuccess:()=>{
    void client.invalidateQueries({queryKey:['gps-preference']})
    void client.invalidateQueries({queryKey:['region-preference']})
  }})
  function suggestRegion() {
    if (!gps?.enabled) return
    if (!window.isSecureContext || !navigator.geolocation) {
      setGpsNote('GPS indisponível. Escolha a região manualmente.')
      return
    }
    setGpsBusy(true)
    navigator.geolocation.getCurrentPosition(
      ({coords}) => {
        setRegion(regionFromPoint(coords.latitude,coords.longitude))
        setAgreed(false)
        setGpsBusy(false)
        setGpsNote('Sugestão aproximada. Confira a região antes de salvar. Coordenadas não foram enviadas.')
      },
      () => {setGpsBusy(false);setGpsNote('Sem localização disponível. Escolha a região manualmente.')},
      {enableHighAccuracy:false,timeout:10000,maximumAge:0},
    )
  }
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
      <div style={{display:'grid',gap:8,marginBottom:14}}>
        <label><input type="checkbox" checked={gps?.enabled ?? false} disabled={gpsMutation.isPending} onChange={e=>{gpsMutation.mutate(e.target.checked);setGpsNote('');if(!e.target.checked){setRegion('');setAgreed(false)}}}/>
          Permitir consulta de localização só quando eu clicar no botão. Opcional e revogável.
        </label>
        <Button variant="secondary" disabled={!gps?.enabled || gpsBusy || gpsMutation.isPending} onClick={suggestRegion}>{gpsBusy?'Consultando GPS...':'Sugerir região pela localização atual'}</Button>
        {gpsNote && <p role="status">{gpsNote}</p>}
        <small>O navegador solicitará permissão separadamente. Sem rastreamento contínuo; coordenadas não são enviadas ao Auto Orbital.</small>
      </div>
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
    <p style={{fontSize:12,opacity:.75}}>Regiões com menos de três participantes ficam ocultas. A retirada do consentimento exclui o registro regional; não há geolocalização automática ou em segundo plano.</p>
  </Panel>
}
