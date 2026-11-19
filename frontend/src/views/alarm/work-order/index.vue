<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { workOrderApi, type WorkOrderItem } from '@/api/alarm'
import { deviceApi, type DeviceItem } from '@/api/device'
import { listUsers, type SysUser } from '@/api/system'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const table = useTable<WorkOrderItem>(workOrderApi.list, {
  status: undefined,
  source: undefined,
  level: undefined,
  type: undefined,
  keyword: '',
})

const deviceOptions = ref<DeviceItem[]>([])
const userOptions = ref<SysUser[]>([])

const levelOptions = [
  { label: '紧急', value: 'critical', tag: 'danger' as const },
  { label: '重要', value: 'major', tag: 'warning' as const },
  { label: '次要', value: 'minor', tag: 'primary' as const },
  { label: '提示', value: 'info', tag: 'info' as const },
]
const statusOptions = [
  { label: '待处理', value: 'pending', tag: 'danger' as const },
  { label: '处理中', value: 'processing', tag: 'warning' as const },
  { label: '已完成', value: 'finished', tag: 'success' as const },
  { label: '已关闭', value: 'closed', tag: 'info' as const },
]
const sourceOptions = [
  { label: '告警转单', value: 'alarm' },
  { label: '手工创建', value: 'manual' },
]
const typeOptions = ['维修', '巡检', '保养'].map((v) => ({ label: v, value: v }))

function levelLabel(v?: string | null) {
  return levelOptions.find((x) => x.value === v)?.label ?? v ?? '-'
}
function levelTag(v?: string | null) {
  return levelOptions.find((x) => x.value === v)?.tag ?? 'info'
}
function statusLabel(v?: string | null) {
  return statusOptions.find((x) => x.value === v)?.label ?? v ?? '-'
}
function statusTag(v?: string | null) {
  return statusOptions.find((x) => x.value === v)?.tag ?? 'info'
}
function sourceLabel(v?: string | null) {
  return sourceOptions.find((x) => x.value === v)?.label ?? v ?? '-'
}

// ---------------- 新建 / 编辑 ----------------
const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  title: '',
  type: '维修',
  level: 'major',
  device_id: undefined as number | undefined | null,
  content: '',
  assignee_id: undefined as number | undefined | null,
})
const formRef = ref<FormInstance>()

function openDialog(row?: WorkOrderItem) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    title: row?.title ?? '',
    type: row?.type ?? '维修',
    level: row?.level ?? 'major',
    device_id: row?.device_id ?? undefined,
    content: row?.content ?? '',
    assignee_id: row?.assignee_id ?? undefined,
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    if (dialog.edit && form.id) await workOrderApi.update(form.id, form)
    else await workOrderApi.create(form)
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.load()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: WorkOrderItem) {
  await ElMessageBox.confirm(`确定删除工单「${row.order_no}」吗？`, '提示', { type: 'warning' })
  await workOrderApi.remove(row.id)
  ElMessage.success('删除成功')
  await table.load()
}

// ---------------- 指派 ----------------
const assignDialog = reactive({ visible: false, saving: false, id: 0, order_no: '', assignee_id: undefined as number | undefined })

function openAssign(row: WorkOrderItem) {
  assignDialog.id = row.id
  assignDialog.order_no = row.order_no
  assignDialog.assignee_id = row.assignee_id ?? undefined
  assignDialog.visible = true
}

async function submitAssign() {
  if (!assignDialog.assignee_id) {
    ElMessage.warning('请选择处理人')
    return
  }
  assignDialog.saving = true
  try {
    await workOrderApi.assign(assignDialog.id, assignDialog.assignee_id)
    ElMessage.success('指派成功')
    assignDialog.visible = false
    await table.load()
  } finally {
    assignDialog.saving = false
  }
}

// ---------------- 处理 ----------------
const handleDialog = reactive({ visible: false, saving: false, id: 0, handle_result: '' })

function openHandle(row: WorkOrderItem) {
  handleDialog.id = row.id
  handleDialog.handle_result = row.handle_result ?? ''
  handleDialog.visible = true
}

async function submitHandle() {
  if (!handleDialog.handle_result.trim()) {
    ElMessage.warning('请填写处理结果')
    return
  }
  handleDialog.saving = true
  try {
    await workOrderApi.handle(handleDialog.id, handleDialog.handle_result)
    ElMessage.success('处理成功')
    handleDialog.visible = false
    await table.load()
  } finally {
    handleDialog.saving = false
  }
}

async function finish(row: WorkOrderItem) {
  const { value } = await ElMessageBox.prompt('请确认或补充处理结果（可留空）', '完成工单', {
    inputValue: row.handle_result ?? '',
    inputPlaceholder: '处理结果',
    inputType: 'textarea',
  })
  await workOrderApi.finish(row.id, value || undefined)
  ElMessage.success('工单已完成')
  await table.load()
}

// ---------------- 详情 ----------------
const detail = reactive({ visible: false, loading: false, data: null as WorkOrderItem | null })

async function openDetail(row: WorkOrderItem) {
  detail.loading = true
  detail.visible = true
  try {
    detail.data = await workOrderApi.get(row.id)
  } finally {
    detail.loading = false
  }
}

async function loadOptions() {
  const [devRes, userRes] = await Promise.all([
    deviceApi.list({ page: 1, page_size: 200 }),
    listUsers({ page: 1, page_size: 200 }),
  ])
  deviceOptions.value = devRes.items
  userOptions.value = userRes.items
}

onMounted(async () => {
  await Promise.all([table.load(), loadOptions()])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>工单管理</h2></div>

      <div class="filter-bar">
        <el-select v-model="table.query.status" placeholder="状态" clearable style="width: 140px" @change="table.search()">
          <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="table.query.source" placeholder="来源" clearable style="width: 140px" @change="table.search()">
          <el-option v-for="s in sourceOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="table.query.level" placeholder="等级" clearable style="width: 120px" @change="table.search()">
          <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
        </el-select>
        <el-select v-model="table.query.type" placeholder="类型" clearable style="width: 120px" @change="table.search()">
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-input
          v-model="table.query.keyword"
          placeholder="工单编号 / 标题"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-button type="primary" @click="openDialog()">新建工单</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="order_no" label="工单编号" width="180" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ row.type || '-' }}</template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{ row }">{{ sourceLabel(row.source) }}</template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备" min-width="150" />
        <el-table-column label="等级" width="90">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处理人" width="110">
          <template #default="{ row }">{{ row.assignee_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'processing'"
              link
              type="primary"
              @click="openAssign(row)"
            >指派</el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'processing'"
              link
              type="warning"
              @click="openHandle(row)"
            >处理</el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'processing'"
              link
              type="success"
              @click="finish(row)"
            >完成</el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="primary"
              @click="openDialog(row)"
            >编辑</el-button>
            <el-button v-if="row.status === 'pending'" link type="danger" @click="remove(row)">删除</el-button>
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
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑工单' : '新建工单'" width="560px">
      <el-form ref="formRef" :model="form" label-width="90px">
        <el-form-item label="标题" prop="title" :rules="[{ required: true, message: '请输入工单标题' }]">
          <el-input v-model="form.title" placeholder="如 光伏逆变器故障维修" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="form.level" style="width: 100%">
            <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联设备">
          <el-select v-model="form.device_id" placeholder="请选择设备" clearable filterable style="width: 100%">
            <el-option v-for="d in deviceOptions" :key="d.id" :label="d.device_name" :value="d.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select v-model="form.assignee_id" placeholder="请选择处理人" clearable filterable style="width: 100%">
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.real_name || u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工单内容">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="请描述工单内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialog.visible" title="指派工单" width="440px">
      <el-form label-width="80px">
        <el-form-item label="工单编号">
          <span>{{ assignDialog.order_no }}</span>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select v-model="assignDialog.assignee_id" placeholder="请选择处理人" filterable style="width: 100%">
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.real_name || u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="assignDialog.saving" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="handleDialog.visible" title="处理工单" width="480px">
      <el-form label-width="80px">
        <el-form-item label="处理结果">
          <el-input v-model="handleDialog.handle_result" type="textarea" :rows="4" placeholder="请填写处理结果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="handleDialog.saving" @click="submitHandle">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detail.visible" title="工单详情" size="480px">
      <el-descriptions v-if="detail.data" :column="1" border v-loading="detail.loading">
        <el-descriptions-item label="工单编号">{{ detail.data.order_no }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ detail.data.title }}</el-descriptions-item>
        <el-descriptions-item label="类型 / 来源">
          {{ detail.data.type || '-' }} / {{ sourceLabel(detail.data.source) }}
        </el-descriptions-item>
        <el-descriptions-item label="设备">{{ detail.data.device_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="等级">
          <el-tag :type="levelTag(detail.data.level)" size="small">{{ levelLabel(detail.data.level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(detail.data.status)" size="small">{{ statusLabel(detail.data.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="处理人">{{ detail.data.assignee_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工单内容">{{ detail.data.content || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处理结果">{{ detail.data.handle_result || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(detail.data.create_time) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDateTime(detail.data.finish_time) }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
