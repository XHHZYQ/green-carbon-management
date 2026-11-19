import { request } from './request'

export interface DashboardOverview {
  device_total: number
  device_online: number
  online_rate: number
  today_energy: number
  month_energy: number
  today_carbon: number
  month_carbon: number
  pending_alarm: number
  month_fee: number
  quota_rate: number
  quota_exceed: number
}

export interface TrendData {
  dates: string[]
  energy: number[]
  carbon: number[]
}

export interface NameValue {
  name: string
  value: number
  ratio?: number
}

export interface CarbonOverview {
  year: number
  total: number
  scopes: NameValue[]
  trend: { months: string[]; values: number[] }
}

export interface DeviceStatus {
  online: NameValue[]
  status: NameValue[]
}

export interface LatestAlarm {
  id: number
  alarm_no: string
  device_name: string
  alarm_level: string
  content: string
  status: string
  alarm_time: string
}

export interface FeeQuota {
  month_fee: number
  prev_fee: number
  fee_mom: number
  quota_total: number
  quota_rate: number
  quota_warning: number
  quota_exceed: number
}

/** 数据驾驶舱 */
export const dashboardApi = {
  overview: () => request<DashboardOverview>({ url: '/dashboard/overview', method: 'get' }),
  energyTrend: (days = 7) =>
    request<TrendData>({ url: '/dashboard/energy-trend', method: 'get', params: { days } }),
  energyItemRatio: () => request<NameValue[]>({ url: '/dashboard/energy-item-ratio', method: 'get' }),
  areaRank: (limit = 8) =>
    request<NameValue[]>({ url: '/dashboard/area-rank', method: 'get', params: { limit } }),
  carbonOverview: (year?: number) =>
    request<CarbonOverview>({ url: '/dashboard/carbon-overview', method: 'get', params: { year } }),
  deviceStatus: () => request<DeviceStatus>({ url: '/dashboard/device-status', method: 'get' }),
  latestAlarms: (limit = 10) =>
    request<LatestAlarm[]>({ url: '/dashboard/latest-alarms', method: 'get', params: { limit } }),
  feeQuota: () => request<FeeQuota>({ url: '/dashboard/fee-quota', method: 'get' }),
}
