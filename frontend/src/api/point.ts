import { request } from './request'
import type { PageResult } from '@/types'

export interface PointItem {
  id?: number
  device_id?: number | null
  device_name?: string
  point_code: string
  point_name: string
  data_type?: string | null
  unit?: string | null
  range_min?: number | null
  range_max?: number | null
  point_type?: string | null
  sort_no: number
  status: number
}

export interface PointTemplateItem {
  id?: number
  template_code: string
  template_name: string
  device_type_id?: number | null
  description?: string | null
  status: number
}

export interface CollectTaskItem {
  id?: number
  device_id?: number | null
  device_name?: string
  task_name: string
  collect_mode?: string | null
  period_sec?: number | null
  range_desc?: string | null
  enable_status: number
  last_run_time?: string | null
}

export interface DeviceDataItem {
  id: number
  device_id?: number | null
  point_id?: number | null
  collect_value?: number | string | null
  unit?: string | null
  data_quality: string
  collect_time?: string | null
}

type Query = Record<string, string | number | undefined>

/** 测点 */
export const pointApi = {
  list: (params?: Query) => request<PageResult<PointItem>>({ url: '/points', method: 'get', params }),
  create: (data: Partial<PointItem>) => request<PointItem>({ url: '/points', method: 'post', data }),
  update: (id: number, data: Partial<PointItem>) => request<PointItem>({ url: `/points/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/points/${id}`, method: 'delete' }),
}

/** 测点模板 */
export const pointTemplateApi = {
  list: (params?: Query) => request<PageResult<PointTemplateItem>>({ url: '/point-templates', method: 'get', params }),
  create: (data: Partial<PointTemplateItem>) => request<PointTemplateItem>({ url: '/point-templates', method: 'post', data }),
  update: (id: number, data: Partial<PointTemplateItem>) =>
    request<PointTemplateItem>({ url: `/point-templates/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/point-templates/${id}`, method: 'delete' }),
}

/** 采集任务 */
export const collectTaskApi = {
  list: (params?: Query) => request<PageResult<CollectTaskItem>>({ url: '/collect-tasks', method: 'get', params }),
  create: (data: Partial<CollectTaskItem>) => request<CollectTaskItem>({ url: '/collect-tasks', method: 'post', data }),
  update: (id: number, data: Partial<CollectTaskItem>) =>
    request<CollectTaskItem>({ url: `/collect-tasks/${id}`, method: 'put', data }),
}

/** 历史数据与补录 */
export const dataApi = {
  list: (params?: Query) => request<PageResult<DeviceDataItem>>({ url: '/data', method: 'get', params }),
  patch: (data: { data_id: number; patch_value: number | string; reason?: string }) =>
    request<unknown>({ url: '/data/patch', method: 'post', data }),
  setQuality: (dataId: number, data_quality: string) =>
    request<unknown>({ url: `/data/${dataId}/quality`, method: 'put', data: { data_quality } }),
}
