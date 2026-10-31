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
  storage?: { status: Status; diagnostic?: Diagnostic | null; collected_at: string | null; used_bytes: number | null; reserved_bytes: number | null; quota_bytes: number | null; warning_percent: number; critical_percent: number; block_percent: number; buckets: { bucket: string; used_bytes: number; objects: number }[] }
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

export interface ClientGeoPoint {
  account: string
  latitude: number
  longitude: number
  accuracy_m: number | null
  collected_at: string
}

export interface ClientGeoOverview {
  status: 'available'
  updated_at: string
  customers_total: number
  recent_active: number
  activity_available: boolean
  gps_points_total: number
  region_participants: number
  deleted_total: number
  deleted_since: string | null
  points: ClientGeoPoint[]
}

export interface OwnGeoPoint {
  latitude: number
  longitude: number
  collected_at: string
}

export const adminMetricsApi = {
  get: (days: number) => api.get<AdminMetrics>(`/admin/metrics?days=${days}`),
  getQueueHealth: () => api.get<AdminQueueHealth>('/admin/queue-health'),
  getOperations: () => api.get<AdminOperations>('/admin/operations'),
  getMyRegion: () => api.get<{region: string | null}>('/admin/my-region'),
  getLocationPoints: () => api.get<ClientGeoOverview>('/admin/location-points'),
  getMyLocation: () => api.get<{point: OwnGeoPoint | null}>('/admin/my-location'),
}

export interface AdminOperations {
  status: 'available' | 'unavailable'
  collected_at: string | null
  database: null | { active: number; idle: number; idle_in_transaction: number; blocked: number; max_connections: number }
  queries: null | { tracked_statements: number; slow_patterns: number; worst: { rank: number; calls: number; mean_ms: number; max_ms: number; total_ms: number }[] }
  uptime: null | { status: 'sampled' | 'no_samples'; ok: number; error: number; unanswered: number; latest: string | null; latest_at: string | null; recent: { at: string; status: 'ok' | 'error' | 'unanswered' }[] }
  costs: { status: 'estimate' | 'not_configured'; monthly_brl: number | null; daily_brl: number | null; note: string }
  acquisition: { status: 'available' | 'unavailable'; source: 'self_reported' | null; minimum_group_size: number; declared_total: number; groups: { source: string; accounts: number }[] }
}
