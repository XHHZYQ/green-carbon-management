import { request } from './request'

type Query = Record<string, string | number | undefined>

export interface PricePlan {
  id?: number
  plan_code: string
  plan_name: string
  energy_type_id?: number | null
  effective_date?: string | null
  expire_date?: string | null
  status: number
  operator_id?: number | null
  created_at?: string | null
  energy_type_name?: string | null
  status_text?: string
  period_count?: number
}

export interface PricePeriod {
  id?: number
  plan_id?: number | null
  period_type: string
  start_time: string
  end_time: string
  day_type: string
  price: number
  sort_no: number
  period_name?: string
  day_type_name?: string
}

export interface PriceHistory {
  id: number
  plan_id?: number | null
  change_desc?: string | null
  old_value?: string | null
  new_value?: string | null
  effective_date?: string | null
  operator_id?: number | null
  changed_at?: string | null
  plan_name?: string | null
  operator_name?: string | null
}

export interface FeeStatItem {
  name: string
  usage: number
  fee: number
  period_type?: string
}

export interface FeeStat {
  summary: { total_usage: number; total_fee: number; avg_price: number }
  items: FeeStatItem[]
}

export interface FeeCompare {
  current: { month: string; usage: number; fee: number }
  mom: { month: string; fee: number; rate: number | null }
  yoy: { month: string; fee: number; rate: number | null }
  period_compare: { name: string; period_type: string; current: number; last: number }[]
}

export interface FeeReportRow {
  month: string
  usage: number
  fee: number
  avg_price: number
}

export interface FeeReport {
  year: number
  rows: FeeReportRow[]
  summary: { month_count: number; total_usage: number; total_fee: number; avg_price: number }
}

/** 电价管理（方案 / 时段 / 调整历史） */
export const priceApi = {
  plans: (params?: Query) => request<PricePlan[]>({ url: '/price/plans', method: 'get', params }),
  createPlan: (data: Partial<PricePlan>) => request<PricePlan>({ url: '/price/plans', method: 'post', data }),
  updatePlan: (id: number, data: Partial<PricePlan>) =>
    request<PricePlan>({ url: `/price/plans/${id}`, method: 'put', data }),
  removePlan: (id: number) => request<null>({ url: `/price/plans/${id}`, method: 'delete' }),

  periods: (planId: number) => request<PricePeriod[]>({ url: `/price/plans/${planId}/periods`, method: 'get' }),
  createPeriod: (planId: number, data: Partial<PricePeriod>) =>
    request<PricePeriod>({ url: `/price/plans/${planId}/periods`, method: 'post', data }),
  updatePeriod: (id: number, data: Partial<PricePeriod>) =>
    request<PricePeriod>({ url: `/price/periods/${id}`, method: 'put', data }),
  removePeriod: (id: number) => request<null>({ url: `/price/periods/${id}`, method: 'delete' }),

  history: (planId: number) => request<PriceHistory[]>({ url: `/price/plans/${planId}/history`, method: 'get' }),
}

/** 费用管理（统计 / 对比 / 报表 / 导出） */
export const feeApi = {
  stat: (dim = 'period') => request<FeeStat>({ url: '/fee/stat', method: 'get', params: { dim } }),
  compare: () => request<FeeCompare>({ url: '/fee/compare', method: 'get' }),
  report: (year?: number) => request<FeeReport>({ url: '/fee/report', method: 'get', params: { year } }),
  export: (year?: number) => request<Blob>({ url: '/fee/export', method: 'get', params: { year }, responseType: 'blob' }),
}
