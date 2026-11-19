<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import type { ElTree } from 'element-plus'
import {
  createRole,
  getRoleMenuIds,
  listMenuTree,
  listRoles,
  removeRole,
  saveRoleMenus,
  updateRole,
  type MenuTreeNode,
  type SysRole,
} from '@/api/system'
import { useTable } from '@/composables/useTable'

const table = useTable<SysRole>(listRoles, { keyword: '' })

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  role_code: '',
  role_name: '',
  description: '',
  sort_no: 0,
  status: 1,
})
const formRef = ref<FormInstance>()

// 菜单权限
const menuTree = ref<MenuTreeNode[]>([])
const treeRef = ref<InstanceType<typeof ElTree>>()
const assign = reactive({ visible: false, roleId: 0, roleName: '', saving: false })

async function loadMenuTree() {
  if (menuTree.value.length) return
  menuTree.value = await listMenuTree()
}

async function openAssign(row: SysRole) {
  await loadMenuTree()
  assign.roleId = row.id!
  assign.roleName = row.role_name
  assign.visible = true
  const ids = await getRoleMenuIds(row.id!)
  await nextTick()
  treeRef.value?.setCheckedKeys(ids, false)
}

async function submitAssign() {
  const checked = treeRef.value?.getCheckedKeys(false) ?? []
  const half = treeRef.value?.getHalfCheckedKeys() ?? []
  assign.saving = true
  try {
    await saveRoleMenus(assign.roleId, [...checked, ...half] as number[])
    ElMessage.success('权限保存成功')
    assign.visible = false
  } finally {
    assign.saving = false
  }
}

function openDialog(row?: SysRole) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    role_code: row?.role_code ?? '',
    role_name: row?.role_name ?? '',
    description: row?.description ?? '',
    sort_no: row?.sort_no ?? 0,
    status: row?.status ?? 1,
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    const payload = {
      role_code: form.role_code,
      role_name: form.role_name,
      description: form.description,
      sort_no: form.sort_no,
      status: form.status,
    }
    if (dialog.edit && form.id) await updateRole(form.id, payload)
    else await createRole(payload)
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.load()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: SysRole) {
  await ElMessageBox.confirm(`确定删除角色「${row.role_name}」吗？`, '提示', { type: 'warning' })
  await removeRole(row.id!)
  ElMessage.success('删除成功')
  await table.load()
}

onMounted(() => table.load())
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>角色管理</h2></div>

      <div class="table-toolbar">
        <el-input
          v-model="table.query.keyword"
          placeholder="角色编码 / 名称"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="openDialog()">新增角色</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="role_code" label="角色编码" min-width="140" />
        <el-table-column prop="role_name" label="角色名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sort_no" label="排序" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openAssign(row)">分配权限</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
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

      <!-- 角色表单 -->
      <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑角色' : '新增角色'" width="480px">
        <el-form ref="formRef" :model="form" label-width="80px">
          <el-form-item label="角色编码" prop="role_code" :rules="[{ required: true, message: '请输入角色编码' }]">
            <el-input v-model="form.role_code" :disabled="dialog.edit" placeholder="如 operator" />
          </el-form-item>
          <el-form-item label="角色名称" prop="role_name" :rules="[{ required: true, message: '请输入角色名称' }]">
            <el-input v-model="form.role_name" placeholder="如 运维人员" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.sort_no" :min="0" />
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

      <!-- 分配权限 -->
      <el-dialog v-model="assign.visible" :title="`分配权限：${assign.roleName}`" width="480px">
        <el-tree
          ref="treeRef"
          :data="menuTree"
          node-key="id"
          show-checkbox
          default-expand-all
          :props="{ label: 'menu_name', children: 'children' }"
        />
        <template #footer>
          <el-button @click="assign.visible = false">取消</el-button>
          <el-button type="primary" :loading="assign.saving" @click="submitAssign">保存</el-button>
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
</style>
