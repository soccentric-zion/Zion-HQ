import type {
  Alarm,
  AlarmRule,
  AuditLogListResponse,
  Backup,
  BackupListResponse,
  Device,
  DeviceAlarm,
  DeviceAlarmListResponse,
  DeviceCreateResponse,
  DeviceListResponse,
  FaultListResponse,
  LogBundleListResponse,
  User,
  UserRole,
} from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // response had no JSON body -- fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  auth: {
    loginUrl: () => request<{ authorization_url: string }>('/auth/login'),
    callback: (code: string, state: string) =>
      request<{ ok: boolean }>(`/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`, {
        method: 'POST',
      }),
    logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
    me: () => request<User>('/auth/me'),
  },
  devices: {
    list: (params: { q?: string; limit?: number; offset?: number } = {}) => {
      const qs = new URLSearchParams()
      if (params.q) qs.set('q', params.q)
      if (params.limit) qs.set('limit', String(params.limit))
      if (params.offset) qs.set('offset', String(params.offset))
      const suffix = qs.toString() ? `?${qs}` : ''
      return request<DeviceListResponse>(`/devices${suffix}`)
    },
    get: (id: string) => request<Device>(`/devices/${id}`),
    create: (name: string) =>
      request<DeviceCreateResponse>('/devices', { method: 'POST', body: JSON.stringify({ name }) }),
    telemetry: (id: string) =>
      request<Record<string, { recorded_at: string; value: number }[]>>(`/devices/${id}/telemetry`),
    factoryReset: (id: string) =>
      request<{ ok: boolean }>(`/devices/${id}/factory-reset`, { method: 'POST' }),
    disable: (id: string) => request<Device>(`/devices/${id}/disable`, { method: 'POST' }),
  },
  faults: {
    list: (deviceId: string) => request<FaultListResponse>(`/devices/${deviceId}/faults`),
  },
  alarms: {
    listForDevice: (deviceId: string) =>
      request<DeviceAlarmListResponse>(`/devices/${deviceId}/alarms`),
    acknowledge: (id: string) => request<Alarm>(`/alarms/${id}/acknowledge`, { method: 'POST' }),
    resolve: (id: string) => request<Alarm>(`/alarms/${id}/resolve`, { method: 'POST' }),
    clear: (deviceId: string, alarmId: string) =>
      request<DeviceAlarm>(`/devices/${deviceId}/alarms/${alarmId}/clear`, { method: 'POST' }),
  },
  alarmRules: {
    list: () => request<AlarmRule[]>('/alarm-rules'),
    create: (name: string, condition: Record<string, unknown>) =>
      request<AlarmRule>('/alarm-rules', { method: 'POST', body: JSON.stringify({ name, condition }) }),
  },
  logs: {
    list: (deviceId: string) => request<LogBundleListResponse>(`/devices/${deviceId}/logs`),
    downloadUrl: (deviceId: string, bundleId: string) =>
      request<{ download_url: string }>(`/devices/${deviceId}/logs/${bundleId}/download`),
  },
  backups: {
    list: (deviceId: string) => request<BackupListResponse>(`/devices/${deviceId}/backups`),
    takeNow: (deviceId: string) => request<Backup>(`/devices/${deviceId}/backups`, { method: 'POST' }),
    restore: (deviceId: string, backupId: string) =>
      request<{ ok: boolean }>(`/devices/${deviceId}/backups/${backupId}/restore`, { method: 'POST' }),
  },
  users: {
    list: () => request<User[]>('/users'),
    invite: (email: string, role: UserRole) =>
      request<User>('/users/invite', { method: 'POST', body: JSON.stringify({ email, role }) }),
  },
  auditLog: {
    list: (params: { limit?: number; offset?: number } = {}) => {
      const qs = new URLSearchParams()
      if (params.limit) qs.set('limit', String(params.limit))
      if (params.offset) qs.set('offset', String(params.offset))
      const suffix = qs.toString() ? `?${qs}` : ''
      return request<AuditLogListResponse>(`/audit-log${suffix}`)
    },
  },
}
