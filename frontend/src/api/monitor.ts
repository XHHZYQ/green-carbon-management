import { request } from './request'
import type { PageResult } from '@/types'

export interface RealtimePoint {
  point_id: number
  point_name: string
  unit?: string | null
  value?: number | null
  collect_time?: string | null
  data_quality?: string | null
}

export interface RealtimeDevice {
  device_id: number
  device_code: string
  device_name: string
  area_name?: string | null
  online_status: string
  points: RealtimePoint[]
}

export interface CurvePoint {
  collect_time: string
  collect_value?: number | null
  data_quality?: string | null
}

export interface TopologyItem {
  id?: number
  topo_code: string
  topo_name: string
  topo_type?: string | null
  area_id?: number | null
  background?: string | null
  remark?: string | null
  status: number
  created_at?: string | null
}

export interface TopologyNode {
  id?: number
  node_key: string
  node_type?: string | null
  device_id?: number | null
  point_id?: number | null
  pos_x?: number | null
  pos_y?: number | null
  width?: number | null
  height?: number | null
  style_json?: Record<string, unknown> | null
  link_json?: Record<string, unknown> | null
  device_name?: string | null
  point_name?: string | null
  unit?: string | null
  value?: number | null
  collect_time?: string | null
}

export interface TopologyDetail extends TopologyItem {
  nodes: TopologyNode[]
}

type Query = Record<string, string | number | undefined>

/** 实时监控 */
export const monitorApi = {
  realtime: (params?: Query) => request<RealtimeDevice[]>({ url: '/monitor/realtime', method: 'get', params }),
  curve: (params: { point_id: number; hours?: number }) =>
    request<CurvePoint[]>({ url: '/monitor/curve', method: 'get', params }),

  topologies: (params?: Query) => request<PageResult<TopologyItem>>({ url: '/monitor/topology', method: 'get', params }),
  topology: (id: number) => request<TopologyDetail>({ url: `/monitor/topology/${id}`, method: 'get' }),
  createTopology: (data: Record<string, unknown>) =>
    request<TopologyDetail>({ url: '/monitor/topology', method: 'post', data }),
  updateTopology: (id: number, data: Record<string, unknown>) =>
    request<TopologyDetail>({ url: `/monitor/topology/${id}`, method: 'put', data }),
  removeTopology: (id: number) => request<null>({ url: `/monitor/topology/${id}`, method: 'delete' }),
}
