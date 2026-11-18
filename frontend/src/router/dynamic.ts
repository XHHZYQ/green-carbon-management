import type { RouteRecordRaw } from 'vue-router'
import type { MenuRoute } from '@/types'

const viewModules = import.meta.glob('../views/**/*.vue')

const PlaceholderView = () => import('@/views/placeholder/index.vue')

export function resolveView(component?: string | null) {
  if (!component) return PlaceholderView
  const key = `../views/${component}.vue`
  return viewModules[key] ?? PlaceholderView
}

/** 将后端菜单树转换为 layout 的子路由（扁平化叶节点） */
export function buildRoutes(menus: MenuRoute[]): RouteRecordRaw[] {
  const routes: RouteRecordRaw[] = []

  const walk = (items: MenuRoute[]) => {
    items.forEach((item) => {
      if (item.component && item.route_path) {
        routes.push({
          path: item.route_path.replace(/^\//, ''),
          name: `Menu_${item.id}`,
          component: resolveView(item.component),
          meta: {
            title: item.menu_name,
            icon: item.icon,
            perm: item.perm_code,
            menuId: item.id,
          },
        })
      }
      if (item.children?.length) walk(item.children)
    })
  }

  walk(menus)
  return routes
}
