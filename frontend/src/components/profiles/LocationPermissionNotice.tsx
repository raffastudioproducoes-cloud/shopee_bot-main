import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi } from '../../api/profiles'
import { useAuthStore } from '../../stores/authStore'
import { Button } from '../ui/Button'

/** Exibido apenas para uma conta que nunca decidiu. Nenhuma leitura de GPS ocorre no mount. */
export function LocationPermissionNotice() {
  const userId = useAuthStore(s => s.user?.id)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['location-sharing', userId],
    queryFn: profilesApi.getLocationSharing,
    enabled: Boolean(userId),
    retry: 1,
    refetchOnMount: 'always',
  })
  const [error, setError] = useState('')
  const [locating, setLocating] = useState(false)
  const decision = useMutation({
    mutationFn: profilesApi.setLocationSharing,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['location-sharing'] })
      void qc.invalidateQueries({ queryKey: ['admin', 'location-points'] })
    },
    onError: () => setError('Não foi possível registrar sua decisão. Tente novamente.'),
  })

  if (!userId || isLoading || data?.choice !== 'pending') return null

  const decline = () => {
    setError('')
    decision.mutate({ choice: 'declined' })
  }

  const allow = () => {
    setError('')
    if (!window.isSecureContext || !navigator.geolocation) {
      // Sem acesso ao serviço do navegador, encerrar a tentativa sem repetir o popup.
      decision.mutate({ choice: 'declined' })
      return
    }

    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      position => {
        // Arredondamento no dispositivo; nunca transmitir a leitura precisa original.
        decision.mutate({
          choice: 'accepted',
          latitude: Number(position.coords.latitude.toFixed(2)),
          longitude: Number(position.coords.longitude.toFixed(2)),
          accuracy_m: Math.max(0, Math.round(position.coords.accuracy)),
        }, { onSettled: () => setLocating(false) })
      },
      () => {
        setLocating(false)
        // Negar o pedido do navegador encerra a decisão: sem novo popup automático.
        decision.mutate({ choice: 'declined' })
      },
      { enableHighAccuracy: false, maximumAge: 0, timeout: 12000 },
    )
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="location-consent-title" aria-describedby="location-consent-detail"
      className="csp-s-0087">
      <div className="csp-s-0088">
        <h2 id="location-consent-title" className="csp-s-0089">Compartilhar sua localização com o Auto Orbital?</h2>
        <div id="location-consent-detail">
          <p>Pedimos sua localização <strong>uma única vez</strong> para identificar onde há clientes e planejar a expansão comercial.</p>
          <p>Se você permitir, o navegador solicitará acesso à localização do dispositivo. Salvaremos coordenadas <strong>aproximadas (arredondadas a cerca de 1 km)</strong>, com data e precisão estimada, vinculadas à sua conta. O administrador poderá visualizar individualmente essa posição aproximada.</p>
          <p>Não coletamos seu endereço por GPS nem monitoramos seus deslocamentos. Você pode recusar e continuar normalmente. Depois, poderá excluir o ponto salvo em <a href="/settings">Configurações</a>; não faremos outra coleta. Veja a <a href="/privacidade" target="_blank" rel="noreferrer">Política de Privacidade</a> e os <a href="/dados-coletados" target="_blank" rel="noreferrer">Dados Coletados</a>.</p>
        </div>
        {error && <p role="alert" className="csp-s-0090">{error}</p>}
        <div className="csp-s-0091">
          <Button variant="secondary" disabled={locating || decision.isPending} onClick={decline}>Não permitir</Button>
          <Button disabled={locating || decision.isPending} onClick={allow}>{locating ? 'Consultando localização...' : 'Permitir uma vez'}</Button>
        </div>
      </div>
    </div>
  )
}
