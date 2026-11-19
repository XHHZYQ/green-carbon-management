import { request } from './request'
import type { PageResult } from '@/types'

type Query = Record<string, string | number | undefined>

export interface CarbonOverview {
  cards: {
    year: number
    total: number
    last_year_total: number
    yoy_rate: number | null
    scope1: number
    scope2: number
    scope3: number
  }
  scope_ratio: { name: string; value: number }[]
  type_ratio: { name: string; value: number }[]
  trend: { months: string[]; values: number[] }
}

export interface CarbonEmissionItem {
  id: number
  period_type?: string | null
  period_value?: string | null
  energy_type_id?: number | null
  area_id?: number | null
  scope?: string | null
  energy_value?: number
  factor_id?: number | null
  factor_value?: number | null
  emission_value?: number
  unit?: string | null
  created_at?: string | null
  energy_type_name?: string | null
  area_name?: string | null
  factor_name?: string | null
}

export interface CarbonReportItem {
  id: number
  report_no: string
  report_name: string
  report_type?: string | null
  period_start?: string | null
  period_end?: string | null
  total_emission?: number | null
  reduction_value?: number | null
  reduction_rate?: number | null
  operator_id?: number | null
  created_at?: string | null
}

export interface CarbonReductionCompare {
  current_year: number
  current_total: number
  last_year_total: number
  yoy_rate: number | null
  reduction: number
  pv_energy: number
  pv_reduction: number
  type_compare: { name: string; current: number; last: number }[]
}

/** 碳排放管理 */
export const carbonApi = {
  overview: (year?: number) => request<CarbonOverview>({ url: '/carbon/overview', method: 'get', params: { year } }),
  calc: (data: { period_type?: string; period_value?: string | null }) =>
    request<{ period_type: string; periods: number; inserted: number }>({ url: '/carbon/calc', method: 'post', data }),

  emissions: (params?: Query) =>
    request<PageResult<CarbonEmissionItem>>({ url: '/carbon/emissions', method: 'get', params }),

  reports: (params?: Query) => request<PageResult<CarbonReportItem>>({ url: '/carbon/reports', method: 'get', params }),
  createReport: (data: { report_name: string; report_type?: string; period_start: string; period_end: string }) =>
    request<CarbonReportItem>({ url: '/carbon/reports', method: 'post', data }),
  exportReport: (id: number) =>
    request<Blob>({ url: `/carbon/reports/${id}/export`, method: 'get', responseType: 'blob' }),

  reductionCompare: () => request<CarbonReductionCompare>({ url: '/carbon/reduction-compare', method: 'get' }),
}
