import { request } from './request'
import type { PageResult } from '@/types'

type Query = Record<string, string | number | undefined>

export interface NotifyChannel {
  id?: number
  channel_code: string
  channel_name: string
  channel_type?: string | null
  config_json?: Record<string, unknown> | null
  enable_status: number
  created_at?: string | null
}

export interface NotifyTemplate {
  id?: number
  template_code: string
  template_name: string
  channel_type?: string | null
  title?: string | null
  content?: string | null
  variables?: string | null
  status: number
  created_at?: string | null
}

export interface NotifyRule {
  id?: number
  rule_name: string
  event_type?: string | null
  condition_json?: Record<string, unknown> | null
  channel_ids?: string | null
  receiver_ids?: string | null
  enable_status: number
  created_at?: string | null
}

export interface NotifyMessage {
  id?: number
  title: string
  content?: string | null
  msg_type?: string | null
  level?: string | null
  receiver_id?: number | null
  receiver_name?: string | null
  read_status: number
  read_time?: string | null
  send_time?: string | null
}

export interface NotifySendLog {
  id?: number
  rule_id?: number | null
  template_id?: number | null
  channel_id?: number | null
  rule_name?: string | null
  template_name?: string | null
  channel_name?: string | null
  receiver?: string | null
  title?: string | null
  content?: string | null
  send_status?: string | null
  error_msg?: string | null
  send_time?: string | null
}

export interface NotifySendPayload {
  title: string
  content?: string
  msg_type?: string
  level?: string
  receiver_ids: number[]
  channel_ids?: number[] | null
}

/** 通用 CRUD 接口生成器 */
function crud<T extends { id?: number }>(base: string) {
  return {
    list: (params?: Query) => request<PageResult<T>>({ url: base, method: 'get', params }),
    create: (data: Partial<T>) => request<T>({ url: base, method: 'post', data }),
    update: (id: number, data: Partial<T>) => request<T>({ url: `${base}/${id}`, method: 'put', data }),
    remove: (id: number) => request<null>({ url: `${base}/${id}`, method: 'delete' }),
  }
}

/** 消息通知 */
export const notifyApi = {
  // 渠道 / 模板 / 规则
  channels: crud<NotifyChannel>('/notify/channels'),
  templates: crud<NotifyTemplate>('/notify/templates'),
  rules: crud<NotifyRule>('/notify/rules'),

  // 站内消息
  messages: (params?: Query) => request<PageResult<NotifyMessage>>({ url: '/notify/messages', method: 'get', params }),
  send: (data: NotifySendPayload) =>
    request<{ message_count: number; log_count: number }>({ url: '/notify/messages', method: 'post', data }),
  markRead: (id: number) => request<null>({ url: `/notify/messages/${id}/read`, method: 'put' }),
  markAllRead: (receiverId?: number) =>
    request<{ updated: number }>({ url: '/notify/messages/read-all', method: 'put', params: { receiver_id: receiverId } }),
  unreadCount: (receiverId?: number) =>
    request<{ count: number }>({ url: '/notify/messages/unread-count', method: 'get', params: { receiver_id: receiverId } }),

  // 发送记录
  sendLogs: (params?: Query) => request<PageResult<NotifySendLog>>({ url: '/notify/send-logs', method: 'get', params }),
}
