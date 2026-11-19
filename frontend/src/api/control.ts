import { request } from './request'
import type { PageResult } from '@/types'

export interface ControlPointItem {
  point_key: string
  point_name: string
  point_type?: string | null
  value_min?: number | null
  value_max?: number | null
  enum_options?: { label: string; value: number | string }[] | null
  dangerous: boolean
  current_value?: string | null
}

export interface ControlDevice {
  device_id: number
  device_code: string
  device_name: string
  area_name?: string | null
  online_status: string
  points: ControlPointItem[]
}

export interface CommandItem {
  id: number
  command_no: string
  device_id?: number | null
  device_name?: string | null
  device_code?: string | null
  point_key?: string | null
  target_value?: string | null
  priority: string
  exec_mode: string
  source?: string | null
  status: string
  status_text?: string
  fail_reason?: string | null
  operator_id?: number | null
  send_time?: string | null
  finish_time?: string | null
  created_at?: string | null
}

export interface TimedTaskItem {
  id: number
  task_name: string
  device_id?: number | null
  device_name?: string | null
  point_key?: string | null
  target_value?: string | null
  cron_expr?: string | null
  repeat_desc?: string | null
  enable_status: number
  last_run_time?: string | null
  next_run_time?: string | null
  created_at?: string | null
}

export const controlApi = {
  points: (params?: Record<string, any>) => request<ControlDevice[]>({ url: '/control/points', method: 'get', params }),
  send: (data: Record<string, any>) => request<CommandItem>({ url: '/control/command', method: 'post', data }),
  batch: (data: Record<string, any>) => request<{ count: number }>({ url: '/control/batch', method: 'post', data }),
  commands: (params?: Record<string, any>) => request<PageResult<CommandItem>>({ url: '/control/commands', method: 'get', params }),
  command: (id: number) => request<CommandItem>({ url: `/control/commands/${id}`, method: 'get' }),
  timedTasks: (params?: Record<string, any>) =>
    request<PageResult<TimedTaskItem>>({ url: '/control/timed-tasks', method: 'get', params }),
  createTimedTask: (data: Record<string, any>) =>
    request<TimedTaskItem>({ url: '/control/timed-tasks', method: 'post', data }),
  updateTimedTask: (id: number, data: Record<string, any>) =>
    request<TimedTaskItem>({ url: `/control/timed-tasks/${id}`, method: 'put', data }),
  removeTimedTask: (id: number) => request<null>({ url: `/control/timed-tasks/${id}`, method: 'delete' }),
}
