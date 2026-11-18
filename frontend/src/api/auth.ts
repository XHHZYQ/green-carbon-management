import { request } from './request'
import type { CaptchaResult, LoginParams, LoginResult, MenuRoute, UserInfo } from '@/types'

export function loginApi(data: LoginParams) {
  return request<LoginResult>({ url: '/auth/login', method: 'post', data })
}

export function getCaptchaApi() {
  return request<CaptchaResult>({ url: '/auth/captcha', method: 'get' })
}

export function logoutApi() {
  return request<null>({ url: '/auth/logout', method: 'post' })
}

export function getMeApi() {
  return request<UserInfo>({ url: '/auth/me', method: 'get' })
}

export function getMenuRoutesApi() {
  return request<MenuRoute[]>({ url: '/menus/routes', method: 'get' })
}

export function changePasswordApi(data: { old_password: string; new_password: string }) {
  return request<null>({ url: '/auth/password', method: 'put', data })
}

export function updateProfileApi(data: Partial<UserInfo>) {
  return request<UserInfo>({ url: '/auth/profile', method: 'put', data })
}
