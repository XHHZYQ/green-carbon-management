import { defineStore } from 'pinia'
import { getMeApi, getMenuRoutesApi, loginApi, logoutApi } from '@/api/auth'
import type { LoginParams, MenuRoute, UserInfo } from '@/types'
import { getToken, getUserCache, removeToken, setToken, setUserCache } from '@/utils/auth'

interface UserState {
  token: string
  userInfo: UserInfo | null
  menus: MenuRoute[]
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: getToken(),
    userInfo: getUserCache<UserInfo>(),
    menus: [],
  }),

  getters: {
    roles: (state) => state.userInfo?.roles ?? [],
    perms: (state) => state.userInfo?.perms ?? [],
    nickname: (state) => state.userInfo?.real_name || state.userInfo?.username || '',
  },

  actions: {
    async login(params: LoginParams) {
      const res = await loginApi(params)
      this.token = res.access_token
      this.userInfo = res.user
      setToken(res.access_token)
      setUserCache(res.user)
      return res
    },

    async loadUserInfo() {
      const info = await getMeApi()
      this.userInfo = info
      setUserCache(info)
      return info
    },

    async loadMenus() {
      const menus = await getMenuRoutesApi()
      this.menus = menus
      return menus
    },

    async logout() {
      try {
        await logoutApi()
      } catch {
        // 忽略退出接口异常
      }
      this.resetState()
    },

    resetState() {
      this.token = ''
      this.userInfo = null
      this.menus = []
      removeToken()
    },

    /** 判断是否拥有某权限码 */
    hasPerm(code?: string | null) {
      if (!code) return true
      const perms = this.perms
      return perms.includes('*') || perms.includes(code)
    },
  },
})
