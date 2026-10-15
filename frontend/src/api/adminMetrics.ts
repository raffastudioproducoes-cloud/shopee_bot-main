import { api } from '../lib/api'

type Status = 'available' | 'partial' | 'unavailable' | 'not_configured'
interface ResourceMetric { value: number; unit: string; timestamp: string; values: number[]; timestamps: string[] }
export interface AdminMetrics {
  status: Status
  updated_at: string
  days: number
  counts: null | { accounts: number; new_accounts: number; deleted_accounts: number; free_accounts: number; plus_accounts: number; premium_accounts: number; active_accounts: number | null; requests: number; errors: number; avg_latency_ms: number | null; p95_latency_ms: number | null }
  daily: { date: string; registrations: number; deletions: number; requests: number }[]
  supabase: { status: Status; database_bytes: number | null; connections: number | null; max_connections: number | null; latency_ms: number | null }
  render: { status: Status; cpu: ResourceMetric | null; memory: ResourceMetric | null; cpu_limit: ResourceMetric | null; memory_limit: ResourceMetric | null; bandwidth: ResourceMetric | null }
  unavailable: { paying_accounts: string; traffic_sources: string; session_time: string; location: string }
  notes: string[]
}
export const adminMetricsApi = { get: (days: number) => api.get<AdminMetrics>(`/admin/metrics?days=${days}`) }
