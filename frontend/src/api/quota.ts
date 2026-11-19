import { request } from './request'
import type { PageResult } from '@/types'

type Query = Record<string, string | number | undefined>

export interface QuotaItem {
  id?: number
  quota_name: string
  quota_type?: string | null
  target_id?: number | null
  energy_type_id?: number | null
  period_type?: string | null
  period_value?: string | null
  quota_value?: number | null
  unit?: string | null
  parent_id?: number | null
  operator_id?: number | null
  created_at?: string | null
  energy_type_name?: string | null
  target_name?: string | null
  parent_name?: string | null
  children?: QuotaItem[]
}

export interface QuotaMonitorItem {
  id: number
  quota_id?: number | null
  period_value?: string | null
  actual_value?: number | null
  quota_value?: number | null
  complete_rate?: number | null
  deviation?: number | null
  warn_status?: string | null
  stat_time?: string | null
  quota_name?: string | null
  unit?: string | null
  quota_type?: string | null
}

export interface QuotaAssessItem {
  id: number
  assess_name: string
  target_id?: number | null
  target_name?: string | null
  period_value?: string | null
  quota_value?: number | null
  actual_value?: number | null
  score?: number | null
  grade?: string | null
  assess_result?: string | null
  assess_time?: string | null
  created_at?: string | null
}

export interface QuotaRefreshResult {
  monitor_count: number
  exceed_count: number
  notified: number
}

export interface QuotaReport {
  cards: { avg_score: number; a_count: number; exceed_count: number; assess_count: number }
  grade_ratio: { name: string; value: number }[]
  score_trend: { periods: string[]; values: number[] }
  list: QuotaAssessItem[]
}

/** 节能定额管理 */
export const quotaApi = {
  quotas: (params?: Query) => request<PageResult<QuotaItem>>({ url: '/quota/quotas', method: 'get', params }),
  createQuota: (data: Partial<QuotaItem>) => request<QuotaItem>({ url: '/quota/quotas', method: 'post', data }),
  updateQuota: (id: number, data: Partial<QuotaItem>) =>
    request<QuotaItem>({ url: `/quota/quotas/${id}`, method: 'put', data }),
  removeQuota: (id: number) => request<null>({ url: `/quota/quotas/${id}`, method: 'delete' }),

  tree: () => request<QuotaItem[]>({ url: '/quota/tree', method: 'get' }),

  monitors: (params?: Query) =>
    request<PageResult<QuotaMonitorItem>>({ url: '/quota/monitors', method: 'get', params }),
  refresh: (data: { period_value?: string | null }) =>
    request<QuotaRefreshResult>({ url: '/quota/monitors/refresh', method: 'post', data }),

  assess: (params?: Query) =>
    request<PageResult<QuotaAssessItem>>({ url: '/quota/assess', method: 'get', params }),
  generateAssess: (data: { period_value: string }) =>
    request<{ count: number }>({ url: '/quota/assess/generate', method: 'post', data }),

  report: (params?: Query) => request<QuotaReport>({ url: '/quota/report', method: 'get', params }),
}
