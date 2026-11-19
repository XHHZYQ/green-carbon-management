import { request } from './request'
import type { PageResult, UserInfo } from '@/types'

export interface SysUser {
  id: number
  username: string
  real_name?: string | null
  phone?: string | null
  email?: string | null
  dept_name?: string | null
  status: number
  avatar?: string | null
  last_login_time?: string | null
  created_at?: string | null
  role_ids: number[]
  role_names: string[]
}

export interface SysRole {
  id?: number
  role_code?: string
  role_name: string
  description?: string | null
  sort_no: number
  status: number
  created_at?: string | null
}

export interface MenuTreeNode {
  id: number
  parent_id: number | null
  menu_name: string
  menu_type: string
  perm_code?: string | null
  children: MenuTreeNode[]
}

export interface OperLog {
  id: number
  username?: string | null
  module?: string | null
  action?: string | null
  method?: string | null
  request_url?: string | null
  ip?: string | null
  status: number
  error_msg?: string | null
  cost_ms: number
  oper_time?: string | null
}

export interface LoginLog {
  id: number
  username?: string | null
  ip?: string | null
  browser?: string | null
  os?: string | null
  status: number
  msg?: string | null
  login_time?: string | null
}

type Query = Record<string, string | number | undefined>

// ---------------- 用户 ----------------
export function listUsers(params?: Query) {
  return request<PageResult<SysUser>>({ url: '/system/users', method: 'get', params })
}
export function createUser(data: Record<string, unknown>) {
  return request<null>({ url: '/system/users', method: 'post', data })
}
export function updateUser(id: number, data: Record<string, unknown>) {
  return request<null>({ url: `/system/users/${id}`, method: 'put', data })
}
export function removeUser(id: number) {
  return request<null>({ url: `/system/users/${id}`, method: 'delete' })
}
export function setUserStatus(id: number, status: number) {
  return request<null>({ url: `/system/users/${id}/status`, method: 'put', data: { status } })
}
export function resetUserPassword(id: number, password: string) {
  return request<null>({ url: `/system/users/${id}/reset-password`, method: 'put', data: { password } })
}

// ---------------- 角色 ----------------
export function listRoles(params?: Query) {
  return request<PageResult<SysRole>>({ url: '/system/roles', method: 'get', params })
}
export function createRole(data: Record<string, unknown>) {
  return request<null>({ url: '/system/roles', method: 'post', data })
}
export function updateRole(id: number, data: Record<string, unknown>) {
  return request<null>({ url: `/system/roles/${id}`, method: 'put', data })
}
export function removeRole(id: number) {
  return request<null>({ url: `/system/roles/${id}`, method: 'delete' })
}
export function listMenuTree() {
  return request<MenuTreeNode[]>({ url: '/system/menus', method: 'get' })
}
export function getRoleMenuIds(roleId: number) {
  return request<number[]>({ url: `/system/roles/${roleId}/menus`, method: 'get' })
}
export function saveRoleMenus(roleId: number, menuIds: number[]) {
  return request<null>({ url: `/system/roles/${roleId}/menus`, method: 'put', data: { menu_ids: menuIds } })
}

// ---------------- 日志 ----------------
export function listOperLogs(params?: Query) {
  return request<PageResult<OperLog>>({ url: '/system/oper-logs', method: 'get', params })
}
export function listLoginLogs(params?: Query) {
  return request<PageResult<LoginLog>>({ url: '/system/login-logs', method: 'get', params })
}

// ---------------- 个人中心 ----------------
export function getProfile() {
  return request<UserInfo>({ url: '/system/profile', method: 'get' })
}
export function updateProfile(data: Record<string, unknown>) {
  return request<UserInfo>({ url: '/system/profile', method: 'put', data })
}
