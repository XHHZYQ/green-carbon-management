import { request } from './request'
import type { PageResult } from '@/types'

type Query = Record<string, string | number | undefined>

export interface AlarmRuleItem {
  id?: number
  rule_name: string
  rule_type?: string | null
  device_id?: number | null
  device_type_id?: number | null
  point_id?: number | null
  operator?: string | null
  threshold?: number | null
  duration_sec?: number
  alarm_level?: string | null
  notify_rule_id?: number | null
  enable_status?: number
  created_at?: string | null
}

export interface AlarmInfoItem {
  id: number
  alarm_no: string
  rule_id?: number | null
  device_id?: number | null
  point_id?: number | null
  alarm_type?: string | null
  alarm_level?: string | null
  alarm_value?: number | null
  threshold?: number | null
  content?: string | null
  status: string
  confirm_by?: number | null
  confirm_time?: string | null
  alarm_time?: string | null
  created_at?: string | null
  device_name?: string | null
  rule_name?: string | null
  confirm_user_name?: string | null
}

export interface AlarmStatistics {
  total: number
  pending: number
  today: number
  by_level: { name: string; value: number }[]
  by_status: { name: string; value: number }[]
  by_type: { name: string; value: number }[]
  trend: { days: string[]; values: number[] }
}

export interface WorkOrderItem {
  id: number
  order_no: string
  title: string
  type?: string | null
  source?: string | null
  alarm_id?: number | null
  device_id?: number | null
  level?: string | null
  status: string
  assignee_id?: number | null
  creator_id?: number | null
  content?: string | null
  handle_result?: string | null
  create_time?: string | null
  finish_time?: string | null
  created_at?: string | null
  device_name?: string | null
  assignee_name?: string | null
}

/** 告警规则通用 CRUD */
const ruleCrud = {
  list: (params?: Query) => request<PageResult<AlarmRuleItem>>({ url: '/alarm/rules', method: 'get', params }),
  create: (data: Partial<AlarmRuleItem>) => request<AlarmRuleItem>({ url: '/alarm/rules', method: 'post', data }),
  update: (id: number, data: Partial<AlarmRuleItem>) =>
    request<AlarmRuleItem>({ url: `/alarm/rules/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/alarm/rules/${id}`, method: 'delete' }),
}

/** 告警中心 */
export const alarmApi = {
  rules: ruleCrud,

  infos: (params?: Query) => request<PageResult<AlarmInfoItem>>({ url: '/alarm/infos', method: 'get', params }),
  getInfo: (id: number) => request<AlarmInfoItem>({ url: `/alarm/infos/${id}`, method: 'get' }),
  confirm: (id: number, data?: { remark?: string }) =>
    request<AlarmInfoItem>({ url: `/alarm/infos/${id}/confirm`, method: 'put', data }),
  handle: (id: number, data?: { remark?: string }) =>
    request<AlarmInfoItem>({ url: `/alarm/infos/${id}/handle`, method: 'put', data }),
  toWorkOrder: (id: number) => request<WorkOrderItem>({ url: `/alarm/infos/${id}/work-order`, method: 'post' }),
  statistics: () => request<AlarmStatistics>({ url: '/alarm/statistics', method: 'get' }),
}

/** 工单管理 */
export const workOrderApi = {
  list: (params?: Query) => request<PageResult<WorkOrderItem>>({ url: '/wo/work-orders', method: 'get', params }),
  get: (id: number) => request<WorkOrderItem>({ url: `/wo/work-orders/${id}`, method: 'get' }),
  create: (data: Partial<WorkOrderItem>) => request<WorkOrderItem>({ url: '/wo/work-orders', method: 'post', data }),
  update: (id: number, data: Partial<WorkOrderItem>) =>
    request<WorkOrderItem>({ url: `/wo/work-orders/${id}`, method: 'put', data }),
  assign: (id: number, assignee_id: number) =>
    request<WorkOrderItem>({ url: `/wo/work-orders/${id}/assign`, method: 'put', data: { assignee_id } }),
  handle: (id: number, handle_result: string) =>
    request<WorkOrderItem>({ url: `/wo/work-orders/${id}/handle`, method: 'put', data: { handle_result } }),
  finish: (id: number, handle_result?: string) =>
    request<WorkOrderItem>({ url: `/wo/work-orders/${id}/finish`, method: 'put', data: { handle_result } }),
  remove: (id: number) => request<null>({ url: `/wo/work-orders/${id}`, method: 'delete' }),
}
