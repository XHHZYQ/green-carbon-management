export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T
}

export interface PageResult<T = unknown> {
  total: number
  items: T[]
}

export interface UserInfo {
  id: number
  username: string
  real_name?: string | null
  phone?: string | null
  email?: string | null
  dept_name?: string | null
  avatar?: string | null
  roles: string[]
  perms: string[]
}

export interface MenuRoute {
  id: number
  parent_id: number | null
  menu_name: string
  route_path: string | null
  component: string | null
  icon: string | null
  perm_code: string | null
  sort_no: number
  visible?: boolean
  children: MenuRoute[]
}

export interface LoginParams {
  username: string
  password: string
  captcha_key?: string
  captcha_code?: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: UserInfo
}

export interface CaptchaResult {
  captcha_key: string
  captcha_image: string
  enabled?: boolean
}
