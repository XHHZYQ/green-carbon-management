import { request } from './request'
import type { PageResult } from '@/types'
import type { DeviceType, Protocol, ProtocolParam } from './config'
import type { PointItem, CollectTaskItem } from './point'

export interface AreaNode {
  id: number
  area_code: string
  area_name: string
  area_type?: string | null
  parent_id?: number | null
  sort_no: number
  status: number
  children?: AreaNode[]
}

export interface DeviceConn {
  id?: number
  device_id?: number
  param_key: string
  param_value: string
}

export interface DeviceItem {
  id?: number
  device_code: string
  device_name: string
  device_type_id?: number | null
  area_id?: number | null
  protocol_id?: number | null
  install_location?: string | null
  status: string
  online_status: string
  access_time?: string | null
  last_online_time?: string | null
  remark?: string | null
  type_name?: string
  protocol_name?: string
  area_name?: string
}

export interface DeviceDetail extends DeviceItem {
  params: DeviceConn[]
  points: PointItem[]
  tasks: CollectTaskItem[]
}

export interface AccessLogItem {
  id: number
  device_id?: number | null
  device_name?: string
  action: string
  result: string
  message?: string | null
  operator_id?: number | null
  cost_ms?: number | null
  access_time?: string | null
}

export interface TestConnResult {
  success: boolean
  message: string
  cost_ms: number
}

export interface ImportResult {
  success: number
  failed: number
  messages: string[]
}

type Query = Record<string, string | number | undefined>

/** 区域分组 */
export const areaApi = {
  tree: () => request<AreaNode[]>({ url: '/areas/tree', method: 'get' }),
  create: (data: Partial<AreaNode>) => request<AreaNode>({ url: '/areas', method: 'post', data }),
  update: (id: number, data: Partial<AreaNode>) => request<AreaNode>({ url: `/areas/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/areas/${id}`, method: 'delete' }),
}

/** 设备台账 */
export const deviceApi = {
  list: (params?: Query) => request<PageResult<DeviceItem>>({ url: '/devices', method: 'get', params }),
  detail: (id: number) => request<DeviceDetail>({ url: `/devices/${id}`, method: 'get' }),
  create: (data: Record<string, unknown>) => request<DeviceItem>({ url: '/devices', method: 'post', data }),
  update: (id: number, data: Record<string, unknown>) =>
    request<DeviceItem>({ url: `/devices/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/devices/${id}`, method: 'delete' }),
  setOnline: (id: number, online: boolean) =>
    request<DeviceItem>({ url: `/devices/${id}/online-status`, method: 'put', data: { online } }),
}

/** 设备接入（向导 / 批量导入 / 接入记录） */
export const accessApi = {
  wizardTypes: () => request<DeviceType[]>({ url: '/devices/wizard/types', method: 'get' }),
  wizardProtocols: (device_type_id?: number) =>
    request<(Protocol & { is_default?: boolean })[]>({
      url: '/devices/wizard/protocols',
      method: 'get',
      params: { device_type_id },
    }),
  wizardParams: (protocol_id?: number) =>
    request<ProtocolParam[]>({ url: '/devices/wizard/params', method: 'get', params: { protocol_id } }),
  testConnection: (data: Record<string, unknown>) =>
    request<TestConnResult>({ url: '/devices/test-connection', method: 'post', data }),
  importTemplate: () => request<Blob>({ url: '/devices/import/template', method: 'get', responseType: 'blob' }),
  importDevices: (form: FormData) =>
    request<ImportResult>({ url: '/devices/import', method: 'post', data: form }),
  logs: (params?: Query) =>
    request<PageResult<AccessLogItem>>({ url: '/devices/access-logs', method: 'get', params }),
}
