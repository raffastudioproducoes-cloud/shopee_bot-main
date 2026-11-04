import { api } from "../lib/api"

export interface ResourceUsage {
  used: number | null
  limit: number | null
  unlimited: boolean
  usage_status: "available" | "unavailable"
}
export type PlanResource = "products" | "lists" | "profiles" | "immediate" | "recurring"
export interface PlanUsage {
  profile_id: string
  plan_tier: "free" | "pro" | "plus" | "premium"
  is_admin: boolean
  campaigns_enabled: boolean
  active_campaigns_limit: number | null
  active_campaigns_count: number | null
  campaign_days: number
  absolute_campaign_days: number
  campaign_posts_per_day: number | null
  automation_entitled: boolean
  automation_available: boolean
  activation_available: boolean
  campaign_paid_through?: string | null
  resources: Record<PlanResource, ResourceUsage>
}
export const planUsageApi = { get: () => api.get<PlanUsage>("/profiles/usage") }
