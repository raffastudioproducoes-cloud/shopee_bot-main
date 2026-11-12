import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { profilesApi, type Profile } from '../api/profiles'
import { useProfileStore } from '../stores/profileStore'
import { deviceTimeZone, getUserTimeZone, setUserTimeZone, shouldAdoptDeviceTimeZone } from '../lib/userTimeZone'
import type { MeResponse } from '../api/auth'

/** Aplica o fuso salvo; conta sem fuso confirmado passa a usar o do dispositivo.
 * Devolve true quando o fuso em uso mudou (telas já desenhadas precisam refazer). */
function syncUserTimeZone(me: MeResponse): boolean {
  const before = getUserTimeZone()
  if (me.timezone) setUserTimeZone(me.timezone)
  const device = deviceTimeZone()
  if (shouldAdoptDeviceTimeZone(me, device)) {
    setUserTimeZone(device)
    authApi.updateTimeZone(device).catch(() => {
      // Sem gravar, a próxima abertura tenta de novo; a tela já usa o fuso local.
    })
  }
  return getUserTimeZone() !== before
}

export const PROFILE_LIMIT = 3

/** Lista de perfis + perfil ativo resolvido (profile_id de /auth/me, senao o principal). */
export function useProfiles() {
  const activeId = useProfileStore((s) => s.activeProfileId)
  const setActive = useProfileStore((s) => s.setActiveProfileId)
  const queryClient = useQueryClient()
  // chave 'profiles' para nao ser invalidada junto dos dados escopados (ver activate)
  const me = useQuery({ queryKey: ['profiles', 'me'], queryFn: () => authApi.me() })
  useEffect(() => {
    if (!me.data) return
    setActive(me.data.profile_id)
    if (syncUserTimeZone(me.data)) {
      queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'profiles' })
    }
  }, [me.data, setActive, queryClient])
  const query = useQuery({ queryKey: ['profiles'], queryFn: () => profilesApi.list() })
  const profiles = query.data ?? []
  const activeProfile: Profile | undefined =
    profiles.find((p) => p.id === activeId) ?? profiles.find((p) => p.kind === 'principal')
  return { ...query, profiles, activeProfile }
}

/** Ativa um perfil e refaz todo dado escopado a perfil, sem reload da pagina. */
export function useActivateProfile() {
  const queryClient = useQueryClient()
  const setActive = useProfileStore((s) => s.setActiveProfileId)
  return useMutation({
    mutationFn: (id: string) => profilesApi.activate(id),
    onSuccess: (_data, id) => {
      setActive(id)
      // tudo, exceto contas de login (users) e a propria lista de perfis
      queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== 'users' && q.queryKey[0] !== 'profiles',
      })
    },
  })
}
