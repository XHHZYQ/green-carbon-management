<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  createUser,
  listRoles,
  listUsers,
  removeUser,
  resetUserPassword,
  setUserStatus,
  updateUser,
  type SysRole,
  type SysUser,
} from '@/api/system'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const table = useTable<SysUser>(listUsers, { keyword: '', status: undefined })
const roleOptions = ref<SysRole[]>([])

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  username: '',
  password: '',
  real_name: '',
  phone: '',
  email: '',
  dept_name: '',
  status: 1,
  role_ids: [] as number[],
})
const formRef = ref<FormInstance>()

function openDialog(row?: SysUser) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    username: row?.username ?? '',
    password: '',
    real_name: row?.real_name ?? '',
    phone: row?.phone ?? '',
    email: row?.email ?? '',
    dept_name: row?.dept_name ?? '',
    status: row?.status ?? 1,
    role_ids: row?.role_ids ?? [],
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    if (dialog.edit && form.id) {
      await updateUser(form.id, {
        real_name: form.real_name,
        phone: form.phone,
        email: form.email,
        dept_name: form.dept_name,
        status: form.status,
        role_ids: form.role_ids,
      })
    } else {
      await createUser({ ...form })
    }
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.load()
  } finally {
    dialog.saving = false
  }
}

async function toggleStatus(row: SysUser) {
  const next = row.status === 1 ? 0 : 1
  await ElMessageBox.confirm(`确定${next === 1 ? '启用' : '停用'}用户「${row.username}」吗？`, '提示', { type: 'warning' })
  await setUserStatus(row.id, next)
  ElMessage.success('操作成功')
  await table.load()
}

async function handleReset(row: SysUser) {
  const { value } = await ElMessageBox.prompt(`重置「${row.username}」的密码（不少于 6 位）`, '重置密码', {
    inputValue: '123456',
    inputPattern: /^.{6,}$/,
    inputErrorMessage: '密码长度不能少于 6 位',
  })
  await resetUserPassword(row.id, value)
  ElMessage.success('密码已重置')
}

async function remove(row: SysUser) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  await removeUser(row.id)
  ElMessage.success('删除成功')
  await table.load()
}

onMounted(async () => {
  await table.load()
  const res = await listRoles({ page: 1, page_size: 100 })
  roleOptions.value = res.items
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>用户管理</h2></div>

      <div class="filter-bar">
        <el-input
          v-model="table.query.keyword"
          placeholder="用户名 / 姓名"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-select v-model="table.query.status" placeholder="全部状态" clearable style="width: 140px" @change="table.search()">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <span class="sub-title">共 {{ table.total }} 个用户</span>
        <el-button type="primary" @click="openDialog()">新增用户</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="real_name" label="姓名" min-width="110" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" min-width="170" show-overflow-tooltip />
        <el-table-column prop="dept_name" label="部门" min-width="120" />
        <el-table-column label="角色" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="name in row.role_names" :key="name" size="small" class="role-tag">{{ name }}</el-tag>
            <span v-if="!row.role_names?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_login_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" @click="toggleStatus(row)">{{ row.status === 1 ? '停用' : '启用' }}</el-button>
            <el-button link type="warning" @click="handleReset(row)">重置密码</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="table-pagination"
        :current-page="table.query.page"
        :page-size="table.query.page_size"
        :total="table.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="table.changePage"
        @size-change="table.changeSize"
      />

      <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑用户' : '新增用户'" width="520px">
        <el-form ref="formRef" :model="form" label-width="80px">
          <el-form-item label="用户名" prop="username" :rules="[{ required: true, message: '请输入用户名' }]">
            <el-input v-model="form.username" :disabled="dialog.edit" placeholder="登录账号" />
          </el-form-item>
          <el-form-item
            v-if="!dialog.edit"
            label="密码"
            prop="password"
            :rules="[{ required: true, message: '请输入密码' }, { min: 6, message: '密码长度不能少于 6 位' }]"
          >
            <el-input v-model="form.password" type="password" show-password placeholder="初始密码" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="form.real_name" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="form.phone" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="form.dept_name" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="form.role_ids" multiple placeholder="请选择角色" style="width: 100%">
              <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id!" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="dialog.saving" @click="submit">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.role-tag {
  margin-right: 4px;
}
</style>
