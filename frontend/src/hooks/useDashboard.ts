import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboard'
import { useAuthStore } from '../stores/authStore'

export function useDashboard() {
  const accountId = useAuthStore((state) => state.user?.id)
  const verified = useAuthStore((state) => state.isRoleVerified)
  return useQuery({
    queryKey: ['dashboard', accountId],
    queryFn: dashboardApi.get,
    enabled: Boolean(accountId && verified),
    gcTime: 0,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: 'always',
  })
}
