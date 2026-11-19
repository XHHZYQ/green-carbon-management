<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { getProfile, updateProfile } from '@/api/system'
import { useUserStore } from '@/store/user'
import type { UserInfo } from '@/types'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const info = ref<UserInfo | null>(null)

const formRef = ref<FormInstance>()
const form = reactive({ real_name: '', phone: '', email: '', dept_name: '' })

async function load() {
  loading.value = true
  try {
    info.value = await getProfile()
    Object.assign(form, {
      real_name: info.value.real_name ?? '',
      phone: info.value.phone ?? '',
      email: info.value.email ?? '',
      dept_name: info.value.dept_name ?? '',
    })
  } finally {
    loading.value = false
  }
}

async function submit() {
  await formRef.value?.validate()
  saving.value = true
  try {
    const data = await updateProfile({ ...form })
    info.value = data
    userStore.userInfo = data
    ElMessage.success('资料更新成功')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16" v-loading="loading">
      <el-col :xs="24" :md="8">
        <div class="page-card profile-card">
          <el-avatar :size="88" class="profile-avatar">{{ userStore.nickname.charAt(0) }}</el-avatar>
          <div class="profile-name">{{ info?.real_name || info?.username }}</div>
          <div class="profile-account">@{{ info?.username }}</div>
          <div class="profile-roles">
            <el-tag v-for="role in info?.roles ?? []" :key="role" size="small">{{ role }}</el-tag>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :md="16">
        <div class="page-card">
          <div class="page-title"><h2>基本资料</h2></div>
          <el-form ref="formRef" :model="form" label-width="90px" style="max-width: 520px">
            <el-form-item label="姓名" prop="real_name">
              <el-input v-model="form.real_name" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email" :rules="[{ type: 'email', message: '邮箱格式不正确' }]">
              <el-input v-model="form.email" />
            </el-form-item>
            <el-form-item label="部门" prop="dept_name">
              <el-input v-model="form.dept_name" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
              <el-button @click="load">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.profile-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
}

.profile-avatar {
  background: #1677ff;
  color: #fff;
  font-size: 34px;
}

.profile-name {
  margin-top: 14px;
  font-size: 18px;
  font-weight: 600;
}

.profile-account {
  margin-top: 4px;
  color: #8a97a8;
  font-size: 13px;
}

.profile-roles {
  margin-top: 14px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
