import { api } from '../lib/api'

export interface DashboardStats {
  products_count: number
  posts_count: number
  lists_count: number
  scheduled_posts: number
  recent_posts: Array<{ id: number; text_preview: string; network: string; created_at: string | null }> | null
  recent_activities: Array<{ id: number; label: string; created_at: string | null }> | null
}

export const dashboardApi = {
  get: () => api.get<DashboardStats>('/dashboard/stats'),
}
