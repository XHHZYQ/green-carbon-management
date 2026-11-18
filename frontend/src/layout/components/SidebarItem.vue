<script setup lang="ts">
import { computed } from 'vue'
import type { MenuRoute } from '@/types'

const props = defineProps<{ menu: MenuRoute }>()

/** 过滤不可见菜单 */
const visibleChildren = computed(() => (props.menu.children ?? []).filter((c) => c.visible !== false))
</script>

<template>
  <!-- 有可见子菜单：渲染为折叠子菜单 -->
  <el-sub-menu v-if="visibleChildren.length" :index="menu.route_path || `sub-${menu.id}`">
    <template #title>
      <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
      <span>{{ menu.menu_name }}</span>
    </template>
    <SidebarItem v-for="child in visibleChildren" :key="child.id" :menu="child" />
  </el-sub-menu>

  <!-- 叶子菜单：渲染为可点击菜单项 -->
  <el-menu-item v-else-if="menu.route_path" :index="menu.route_path">
    <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
    <template #title>{{ menu.menu_name }}</template>
  </el-menu-item>
</template>
