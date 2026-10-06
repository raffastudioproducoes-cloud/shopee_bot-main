import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { profilesApi, type Profile } from '../api/profiles'
import { useProfileStore } from '../stores/profileStore'

export const PROFILE_LIMIT = 3

/** Lista de perfis + perfil ativo resolvido (id salvo, senao o principal). */
export function useProfiles() {
  const activeId = useProfileStore((s) => s.activeProfileId)
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
