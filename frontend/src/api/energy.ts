import { request } from './request'

type Query = Record<string, string | number | undefined>

export interface EnergyOverviewCards {
  month_energy: number
  month_fee: number
  month_carbon: number
  today_energy: number
  mom_rate: number | null
  yoy_rate: number | null
}

export interface EnergyOverview {
  cards: EnergyOverviewCards
  trend: { dates: string[]; values: number[] }
  type_ratio: { name: string; value: number }[]
  area_rank: { name: string; value: number }[]
}

export interface EnergyAnalysisItem {
  name: string
  value: number
  ratio: number
  rank?: number
}

export interface PeakValleyItem {
  period_type: string
  period_name: string
  usage: number
  price: number
  fee: number
  fee_ratio: number
}

export interface EnergyCost {
  trend: { months: string[]; energy: number[]; fee: number[] }
  period_fee: { name: string; value: number }[]
}

/** 能耗管理 */
export const energyApi = {
  overview: () => request<EnergyOverview>({ url: '/energy/overview', method: 'get' }),
  analysis: (params?: Query) => request<EnergyAnalysisItem[]>({ url: '/energy/analysis', method: 'get', params }),
  itemRatio: (params?: Query) => request<EnergyAnalysisItem[]>({ url: '/energy/item-ratio', method: 'get', params }),
  peakValley: (params?: Query) => request<PeakValleyItem[]>({ url: '/energy/peak-valley', method: 'get', params }),
  rank: (params?: Query) => request<EnergyAnalysisItem[]>({ url: '/energy/rank', method: 'get', params }),
  cost: (months = 6) => request<EnergyCost>({ url: '/energy/cost', method: 'get', params: { months } }),
  export: (params?: Query) => request<Blob>({ url: '/energy/export', method: 'get', params, responseType: 'blob' }),
}
