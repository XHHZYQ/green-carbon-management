import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Layout from '@/layout/index.vue'
import { useUserStore } from '@/store/user'
import { getToken } from '@/utils/auth'
import { buildRoutes } from './dynamic'

export const LAYOUT_NAME = 'Layout'

const requireViews = import.meta.glob('../views/**/*.vue')

const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    name: LAYOUT_NAME,
    component: Layout,
    redirect: '/dashboard',
    children: [],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes,
  scrollBehavior: () => ({ top: 0 }),
})

let dynamicAdded = false

function ensureDashboard() {
  const hasDashboard = router.getRoutes().some((r) => r.path === '/dashboard')
  if (!hasDashboard) {
    router.addRoute(LAYOUT_NAME, {
      path: 'dashboard',
      name: 'Dashboard',
      component: requireViews['../views/dashboard/index.vue'],
      meta: { title: '数据驾驶舱', icon: 'Odometer' },
    })
  }
}

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (to.path === '/login') {
    return getToken() ? { path: '/' } : true
  }

  if (!getToken()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!dynamicAdded) {
    try {
      if (!userStore.userInfo) await userStore.loadUserInfo()
      const menus = await userStore.loadMenus()
      buildRoutes(menus).forEach((route) => router.addRoute(LAYOUT_NAME, route))
      ensureDashboard()
      dynamicAdded = true
      // 仅按路径重定向，避免携带 404 路由的 name 导致重新匹配到 404
      return { path: to.path, query: to.query, hash: to.hash, replace: true }
    } catch {
      userStore.resetState()
      return { path: '/login' }
    }
  }

  return true
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) || ''
  document.title = title ? `${title} - ${import.meta.env.VITE_APP_TITLE}` : import.meta.env.VITE_APP_TITLE
})

export function resetRouter() {
  dynamicAdded = false
}

export default router
