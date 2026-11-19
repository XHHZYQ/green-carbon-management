import { request } from './request'
import type { PageResult } from '@/types'

export interface DictType {
  id?: number
  type_code: string
  type_name: string
  remark?: string | null
  status: number
  created_at?: string
}

export interface DictItem {
  id?: number
  type_id?: number | null
  item_label: string
  item_value: string
  sort_no: number
  status: number
  remark?: string | null
}

export interface EnergyType {
  id?: number
  type_code: string
  type_name: string
  unit?: string | null
  sort_no: number
  status: number
}

export interface EnergyItem {
  id?: number
  item_code: string
  item_name: string
  parent_id?: number | null
  energy_type_id?: number | null
  sort_no: number
  status: number
}

export interface CarbonFactor {
  id?: number
  energy_type_id?: number | null
  factor_name: string
  factor_value?: number | null
  factor_unit?: string | null
  scope?: string | null
  effective_date?: string | null
  expire_date?: string | null
  status: number
}

export interface DeviceType {
  id?: number
  type_code: string
  type_name: string
  category?: string | null
  default_protocol_id?: number | null
  icon?: string | null
  sort_no: number
  status: number
}

export interface Protocol {
  id?: number
  protocol_code: string
  protocol_name: string
  category?: string | null
  description?: string | null
  status: number
}

export interface ProtocolParam {
  id?: number
  protocol_id?: number | null
  param_key: string
  param_label: string
  param_type: string
  required: boolean
  default_value?: string | null
  options?: unknown
  sort_no: number
}

export interface SystemParam {
  id?: number
  param_key: string
  param_value?: string | null
  param_name: string
  param_group?: string | null
  remark?: string | null
  updated_at?: string
}

type Query = Record<string, string | number | undefined>

/** 通用 CRUD 接口生成器 */
function crud<T extends { id?: number }>(base: string) {
  return {
    list: (params?: Query) => request<PageResult<T>>({ url: base, method: 'get', params }),
    create: (data: Partial<T>) => request<T>({ url: base, method: 'post', data }),
    update: (id: number, data: Partial<T>) => request<T>({ url: `${base}/${id}`, method: 'put', data }),
    remove: (id: number) => request<null>({ url: `${base}/${id}`, method: 'delete' }),
  }
}

export const dictTypeApi = crud<DictType>('/config/dict-types')
export const dictItemApi = crud<DictItem>('/config/dict-items')
export const energyTypeApi = crud<EnergyType>('/config/energy-types')
export const energyItemApi = crud<EnergyItem>('/config/energy-items')
export const carbonFactorApi = crud<CarbonFactor>('/config/carbon-factors')
export const deviceTypeApi = crud<DeviceType>('/config/device-types')
export const protocolApi = crud<Protocol>('/config/protocols')
export const protocolParamApi = crud<ProtocolParam>('/config/protocol-params')

export function listSystemParams() {
  return request<SystemParam[]>({ url: '/config/system-params', method: 'get' })
}

export function saveSystemParams(data: SystemParam[]) {
  return request<null>({ url: '/config/system-params', method: 'put', data })
}
