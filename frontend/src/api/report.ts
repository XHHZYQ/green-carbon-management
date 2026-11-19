import { request } from './request'
import type { PageResult } from '@/types'

type Query = Record<string, string | number | undefined>

export interface ReportTemplateItem {
  id?: number
  template_code: string
  template_name: string
  report_type?: string | null
  data_source?: string | null
  dimension_json?: unknown
  columns_json?: unknown
  status?: number
  created_at?: string | null
}

export interface ReportRecordItem {
  id: number
  template_id?: number | null
  template_name?: string | null
  report_name: string
  report_type?: string | null
  period_start?: string | null
  period_end?: string | null
  file_type?: string | null
  file_path?: string | null
  gen_status?: string | null
  gen_time?: string | null
  operator_id?: number | null
}

export interface ReportSubscribeItem {
  id?: number
  template_id?: number | null
  template_name?: string | null
  subscribe_name: string
  cron_expr?: string | null
  receivers?: string | null
  channel_ids?: string | null
  enable_status?: number
  last_send_time?: string | null
}

export interface ReportGeneratePayload {
  template_id?: number | null
  report_name?: string
  report_type?: string
  period_start?: string | null
  period_end?: string | null
  file_type?: string
}

export interface ReportCustomPayload {
  report_name: string
  data_source: string
  dimension: string
  period_start?: string | null
  period_end?: string | null
}

/** 报表中心 */
export const reportApi = {
  templates: (params?: Query) =>
    request<ReportTemplateItem[]>({ url: '/reports/templates', method: 'get', params }),
  createTemplate: (data: Partial<ReportTemplateItem>) =>
    request<ReportTemplateItem>({ url: '/reports/templates', method: 'post', data }),
  updateTemplate: (id: number, data: Partial<ReportTemplateItem>) =>
    request<ReportTemplateItem>({ url: `/reports/templates/${id}`, method: 'put', data }),
  removeTemplate: (id: number) => request<null>({ url: `/reports/templates/${id}`, method: 'delete' }),

  generate: (data: ReportGeneratePayload) =>
    request<ReportRecordItem>({ url: '/reports/generate', method: 'post', data }),
  custom: (data: ReportCustomPayload) =>
    request<ReportRecordItem>({ url: '/reports/custom', method: 'post', data }),

  records: (params?: Query) =>
    request<PageResult<ReportRecordItem>>({ url: '/reports/records', method: 'get', params }),
  exportRecord: (id: number, fileType: string) =>
    request<Blob>({
      url: `/reports/records/${id}/export`,
      method: 'get',
      params: { file_type: fileType },
      responseType: 'blob',
    }),

  subscriptions: (params?: Query) =>
    request<PageResult<ReportSubscribeItem>>({ url: '/reports/subscriptions', method: 'get', params }),
  createSubscription: (data: Partial<ReportSubscribeItem>) =>
    request<ReportSubscribeItem>({ url: '/reports/subscriptions', method: 'post', data }),
  updateSubscription: (id: number, data: Partial<ReportSubscribeItem>) =>
    request<ReportSubscribeItem>({ url: `/reports/subscriptions/${id}`, method: 'put', data }),
  removeSubscription: (id: number) =>
    request<null>({ url: `/reports/subscriptions/${id}`, method: 'delete' }),
  runSubscription: (id: number) =>
    request<{ record_id: number; report_name: string; receiver_count: number; channel_count: number }>({
      url: `/reports/subscriptions/${id}/run`,
      method: 'post',
    }),
}
