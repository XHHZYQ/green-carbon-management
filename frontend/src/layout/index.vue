<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import SidebarItem from './components/SidebarItem.vue'
import { resetRouter } from '@/router'
import { useUserStore } from '@/store/user'
import { changePasswordApi } from '@/api/auth'
import type { MenuRoute } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const activeMenu = computed(() => route.path)

/** 在菜单树中查找目标路径，返回从根到该节点的链路 */
function findMenuPath(menus: MenuRoute[], path: string, chain: MenuRoute[] = []): MenuRoute[] {
  for (const menu of menus) {
    const next = [...chain, menu]
    if (menu.route_path === path) return next
    if (menu.children?.length) {
      const found = findMenuPath(menu.children, path, next)
      if (found.length) return found
    }
  }
  return []
}

const breadcrumbs = computed(() => {
  const chain = findMenuPath(userStore.menus, route.path)
  if (chain.length) return chain.map((m) => m.menu_name)
  return [(route.meta.title as string) || '首页']
})

async function handleCommand(command: string) {
  if (command === 'profile') {
    router.push('/system/profile')
  } else if (command === 'password') {
    passwordVisible.value = true
  } else if (command === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    await userStore.logout()
    resetRouter()
    router.push('/login')
  }
}

// ===== 修改密码 =====
const passwordVisible = ref(false)
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    {
      validator: (_r: unknown, value: string, cb: (e?: Error) => void) =>
        value === passwordForm.new_password ? cb() : cb(new Error('两次输入的密码不一致')),
      trigger: 'blur',
    },
  ],
}

async function submitPassword() {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate()
  await changePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
  ElMessage.success('密码修改成功，请重新登录')
  passwordVisible.value = false
  await userStore.logout()
  router.push('/login')
}

function resetPasswordForm() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate()
}
</script>

<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside class="layout-aside" :width="isCollapse ? '64px' : '230px'">
      <div class="layout-logo">
        <el-icon class="logo-icon"><Lightning /></el-icon>
        <span v-show="!isCollapse" class="logo-text">绿色低碳管控</span>
      </div>
      <el-scrollbar class="layout-menu-wrap">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :collapse-transition="false"
          router
          background-color="transparent"
          text-color="#b7c7e0"
          active-text-color="#ffffff"
        >
          <SidebarItem v-for="menu in userStore.menus" :key="menu.id" :menu="menu" />
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="layout-body">
      <!-- 顶栏 -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="(item, idx) in breadcrumbs" :key="idx">{{ item }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" class="user-avatar">{{ userStore.nickname.charAt(0) }}</el-avatar>
              <span class="user-name">{{ userStore.nickname }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 修改密码弹窗 -->
    <el-dialog
      v-model="passwordVisible"
      title="修改密码"
      width="420px"
      @closed="resetPasswordForm"
    >
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="88px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.layout {
  height: 100vh;
}

.layout-aside {
  background: $sidebar-bg;
  transition: width 0.28s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.layout-logo {
  height: $header-height;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  color: #fff;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.04);

  .logo-icon {
    font-size: 24px;
    color: $primary-color;
  }

  .logo-text {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
  }
}

.layout-menu-wrap {
  flex: 1;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  &:hover {
    background-color: $sidebar-bg-light !important;
  }
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, $primary-color, rgba(22, 119, 255, 0.6)) !important;
  border-radius: 0 20px 20px 0;
}

.layout-body {
  flex-direction: column;
  overflow: hidden;
}

.layout-header {
  height: $header-height;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 6px rgba(9, 30, 66, 0.06);
  z-index: 5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;

  .collapse-btn {
    font-size: 20px;
    cursor: pointer;
    color: $text-regular;

    &:hover {
      color: $primary-color;
    }
  }
}

.header-right {
  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    outline: none;
  }

  .user-avatar {
    background: $primary-color;
    color: #fff;
    font-size: 14px;
  }

  .user-name {
    font-size: 14px;
    color: $text-primary;
  }
}

.layout-main {
  background: $page-bg;
  padding: 16px;
  overflow-y: auto;
}
</style>
