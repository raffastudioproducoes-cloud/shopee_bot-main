import { useQuery } from "@tanstack/react-query"
import { planUsageApi } from "../api/planUsage"
import { useAuthStore } from "../stores/authStore"
import { useProfileStore } from "../stores/profileStore"

export function usePlanUsage() {
  const userId = useAuthStore((state) => state.user?.id)
  const verified = useAuthStore((state) => state.isRoleVerified)
  const profileId = useProfileStore((state) => state.activeProfileId)
  return useQuery({
    queryKey: ["plan-usage", userId, profileId],
    queryFn: planUsageApi.get,
    enabled: Boolean(userId && profileId && verified),
    staleTime: 0,
    retry: false,
    refetchOnWindowFocus: "always",
  })
}
