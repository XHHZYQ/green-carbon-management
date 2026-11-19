import { request } from './request'
import type { PageResult } from '@/types'

export interface SceneActionItem {
  id: number
  scene_id?: number | null
  device_id?: number | null
  device_name?: string | null
  point_key?: string | null
  target_value?: string | null
  delay_sec: number
  sort_no: number
}

export interface SceneItem {
  id: number
  scene_code: string
  scene_name: string
  icon?: string | null
  description?: string | null
  enable_status: number
  last_exec_time?: string | null
  action_count?: number
  cron_expr?: string | null
  repeat_desc?: string | null
  schedule_enable?: number
  next_run_time?: string | null
  actions?: SceneActionItem[]
}

export interface LinkRuleItem {
  id: number
  rule_name: string
  condition_text?: string | null
  condition_json?: Record<string, any> | null
  action_type?: string | null
  target_scene_id?: number | null
  target_scene_name?: string | null
  target_device_id?: number | null
  target_device_name?: string | null
  target_point_key?: string | null
  target_value?: string | null
  enable_status: number
  created_at?: string | null
}

export interface SceneExecLogItem {
  id: number
  exec_type?: string | null
  exec_type_text?: string | null
  scene_id?: number | null
  scene_name?: string | null
  rule_id?: number | null
  rule_name?: string | null
  trigger_source?: string | null
  total_count: number
  success_count: number
  fail_count: number
  result?: string | null
  result_text?: string | null
  exec_time?: string | null
}

export const sceneApi = {
  list: (params?: Record<string, any>) => request<PageResult<SceneItem>>({ url: '/scenes', method: 'get', params }),
  detail: (id: number) => request<SceneItem>({ url: `/scenes/${id}`, method: 'get' }),
  create: (data: Record<string, any>) => request<SceneItem>({ url: '/scenes', method: 'post', data }),
  update: (id: number, data: Record<string, any>) => request<SceneItem>({ url: `/scenes/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/scenes/${id}`, method: 'delete' }),
  setEnable: (id: number, enable_status: number) =>
    request<SceneItem>({ url: `/scenes/${id}/enable`, method: 'put', data: { enable_status } }),
  exec: (id: number) =>
    request<{ total_count: number; success_count: number; fail_count: number; result: string }>({
      url: `/scenes/${id}/exec`,
      method: 'post',
    }),
  saveSchedule: (id: number, data: Record<string, any>) =>
    request<Record<string, any>>({ url: `/scenes/${id}/schedule`, method: 'post', data }),
  actions: (id: number) => request<SceneActionItem[]>({ url: `/scenes/${id}/actions`, method: 'get' }),
  createAction: (id: number, data: Record<string, any>) =>
    request<SceneActionItem>({ url: `/scenes/${id}/actions`, method: 'post', data }),
  updateAction: (actionId: number, data: Record<string, any>) =>
    request<SceneActionItem>({ url: `/scenes/actions/${actionId}`, method: 'put', data }),
  removeAction: (actionId: number) => request<null>({ url: `/scenes/actions/${actionId}`, method: 'delete' }),

  linkRules: (params?: Record<string, any>) =>
    request<PageResult<LinkRuleItem>>({ url: '/link-rules', method: 'get', params }),
  createLinkRule: (data: Record<string, any>) => request<LinkRuleItem>({ url: '/link-rules', method: 'post', data }),
  updateLinkRule: (id: number, data: Record<string, any>) =>
    request<LinkRuleItem>({ url: `/link-rules/${id}`, method: 'put', data }),
  removeLinkRule: (id: number) => request<null>({ url: `/link-rules/${id}`, method: 'delete' }),
  setLinkEnable: (id: number, enable_status: number) =>
    request<LinkRuleItem>({ url: `/link-rules/${id}/enable`, method: 'put', data: { enable_status } }),

  execLogs: (params?: Record<string, any>) =>
    request<PageResult<SceneExecLogItem>>({ url: '/scene-exec-logs', method: 'get', params }),
}
