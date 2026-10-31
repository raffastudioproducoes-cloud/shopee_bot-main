import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi } from '../../api/profiles'
import { useAuthStore } from '../../stores/authStore'
import { Button } from '../ui/Button'

export function LocationPermissionNotice() {
  const authed = useAuthStore(s=>s.isAuthenticated)
  const qc = useQueryClient()
  const {data,isLoading} = useQuery({queryKey:['location-sharing'],queryFn:profilesApi.getLocationSharing,enabled:authed,retry:1})
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(false)
  const decision=useMutation({mutationFn:profilesApi.setLocationSharing,onSuccess:()=>{void qc.invalidateQueries({queryKey:['location-sharing']});void qc.invalidateQueries({queryKey:['admin','location-points']})}})
  if (!authed || isLoading || !data || data.choice!=='pending') return null
  const decline=()=>{setError('');decision.mutate({choice:'declined'})}
  const allow=()=>{
    setError('')
    if (!window.isSecureContext || !navigator.geolocation) {setError('Seu navegador não disponibiliza geolocalização. Você pode recusar e continuar normalmente.');return}
    setLoading(true)
    navigator.geolocation.getCurrentPosition(
      pos => {
        // Quantização no próprio dispositivo: precisão de cerca de 1 km, sem histórico de trajeto.
        decision.mutate({choice:'accepted',latitude:Number(pos.coords.latitude.toFixed(2)),longitude:Number(pos.coords.longitude.toFixed(2)),accuracy_m:Math.max(0,Math.round(pos.coords.accuracy))},{onError:()=>setError('Não foi possível registrar sua escolha. Tente novamente.'),onSettled:()=>setLoading(false)})
      },
      ()=>{setLoading(false);setError('Localização não autorizada ou indisponível. Você pode recusar e continuar usando o site.')},
      {enableHighAccuracy:false,maximumAge:0,timeout:12000},
    )
  }
  return <div role="dialog" aria-modal="true" aria-labelledby="location-consent-title" style={{position:'fixed',inset:0,zIndex:9999,background:'rgba(0,0,0,.72)',display:'grid',placeItems:'center',padding:16}}>
    <div style={{background:'var(--surface-card)',color:'var(--text-body)',border:'1px solid var(--border-hairline)',borderRadius:12,padding:26,maxWidth:560,width:'100%',boxShadow:'0 20px 70px rgba(0,0,0,.6)'}}>
      <h2 id="location-consent-title" style={{marginTop:0}}>Compartilhar localização com o Auto Orbital?</h2>
      <p>O Auto Orbital solicita sua localização <strong>uma única vez</strong>, com sua autorização, para identificar regiões onde há clientes e planejar a expansão comercial dos serviços.</p>
      <p>Se permitir, o navegador solicitará acesso ao GPS ou localização do dispositivo. Enviaremos ao servidor apenas coordenadas <strong>aproximadas, arredondadas a cerca de 1 km</strong>, vinculadas à sua conta, com data e precisão estimada. O administrador poderá visualizar essa região individualmente. Não coletamos endereço nem acompanhamos deslocamentos.</p>
      <p>É opcional. Você pode recusar sem perder acesso, e retirar a autorização em <a href="/settings">Configurações</a>. Consulte <a href="/privacidade" target="_blank" rel="noreferrer">Privacidade</a> e <a href="/dados-coletados" target="_blank" rel="noreferrer">Dados coletados</a>.</p>
      {error && <p role="alert">{error}</p>}
      {decision.isError && <p role="alert">Não foi possível salvar a decisão. Tente novamente.</p>}
      <div style={{display:'flex',gap:12,justifyContent:'flex-end',flexWrap:'wrap'}}>
        <Button variant="secondary" disabled={loading||decision.isPending} onClick={decline}>Não permitir</Button>
        <Button disabled={loading||decision.isPending} onClick={allow}>{loading?'Consultando localização...':'Permitir localização'}</Button>
      </div>
    </div>
  </div>
}
