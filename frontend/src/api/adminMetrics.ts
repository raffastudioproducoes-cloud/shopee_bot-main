import { api } from '../lib/api'

type Status = 'available' | 'partial' | 'unavailable' | 'not_configured'
type Diagnostic = 'timeout' | 'permission_denied' | 'rpc_missing' | 'invalid_response' | 'provider_error' | 'api_rejected' | 'bad_request' | 'no_samples' | 'not_configured'
interface ResourceMetric { value: number; unit: string; timestamp: string; values: number[]; timestamps: string[] }
export interface AdminMetrics {
  status: Status
  updated_at: string
  days: number
  counts: null | { accounts: number; new_accounts: number; deleted_accounts: number; free_accounts: number; plus_accounts: number; premium_accounts: number; active_accounts: number | null; requests: number; errors: number; avg_latency_ms: number | null; p95_latency_ms: number | null }
  daily: { date: string; registrations: number; deletions: number; requests: number }[]
  supabase: { status: Status; diagnostic?: Diagnostic | null; database_bytes: number | null; connections: number | null; max_connections: number | null; latency_ms: number | null }
  render: { status: Status; diagnostic?: Diagnostic | null; missing_metrics?: string[]; cpu: ResourceMetric | null; memory: ResourceMetric | null; cpu_limit: ResourceMetric | null; memory_limit: ResourceMetric | null; bandwidth: ResourceMetric | null }
  unavailable: { paying_accounts: string; traffic_sources: string; session_time: string; location: string }
  notes: string[]
  geography?: { status: 'available' | 'not_configured'; updated_at: string | null; regions: { region: string; online: number; offline: number; deleted: number }[] }
  scale?: null | {
    collected_at?: string | null
    capacity_history?: { date: string; database_bytes: number; observed_connections: number }[]
    consumption?: { plan: 'free' | 'plus' | 'premium' | 'unknown'; requests: number; request_duration_ms: number }[]
    server_errors: number | null; rate_limited_requests: number | null; p99_latency_ms: number | null
    database: null | { blocked_connections: number; oldest_transaction_seconds: number | null; tables: { name: string; table_bytes: number; index_bytes: number }[] }
    operations: null | { scheduled: number; published_events: number; failed_events: number; publishing_accounts: number }
    engagement: null | { active_week: number; previous_week: number; returning_week: number }
  }
  previous_period?: { starts_on: string; ends_on: string; registrations: number; deletions: number; requests: number; errors: number } | null
}
export interface AdminQueueHealth {
  status: 'available' | 'unavailable'
  counts: null | {
    total: number
    pending: number
    running: number
    unknown: number
    reported_removed: number
    failed: number
    succeeded: number
    manually_confirmed: number
    multiple_attempts: number
  }
  oldest_unknown_minutes: number | null
  oldest_running_minutes: number | null
  last_started_at: string | null
  collected_at: string | null
}

export const adminMetricsApi = {
  get: (days: number) => api.get<AdminMetrics>(`/admin/metrics?days=${days}`),
  getQueueHealth: () => api.get<AdminQueueHealth>('/admin/queue-health'),
}
