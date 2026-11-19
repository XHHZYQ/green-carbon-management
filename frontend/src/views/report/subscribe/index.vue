<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { reportApi, type ReportSubscribeItem, type ReportTemplateItem } from '@/api/report'
import { listUsers, type SysUser } from '@/api/system'
import { notifyApi, type NotifyChannel } from '@/api/notify'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const cronOptions = [
  { label: '每天 08:00', value: '0 0 8 * * ?' },
  { label: '每周一 08:00', value: '0 0 8 ? * MON' },
  { label: '每月 1 日 08:00', value: '0 0 8 1 * ?' },
  { label: '每季度首日 08:00', value: '0 0 8 1 1,4,7,10 ?' },
]

const table = useTable<ReportSubscribeItem>(reportApi.subscriptions, {
  page_size: 10,
  subscribe_name: '',
})

const templates = ref<ReportTemplateItem[]>([])
const users = ref<SysUser[]>([])
const channels = ref<NotifyChannel[]>([])

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  template_id: undefined as number | undefined,
  subscribe_name: '',
  cron_expr: '0 0 8 * * ?',
  receiver_ids: [] as number[],
  channel_ids: [] as number[],
  enable_status: 1,
})
const formRef = ref<FormInstance>()

function parseIds(value?: string | null): number[] {
  return (value ?? '')
    .replace(/，/g, ',')
    .split(',')
    .map((x) => x.trim())
    .filter((x) => x !== '')
    .map((x) => Number(x))
    .filter((x) => !Number.isNaN(x))
}

function templateName(id?: number | null) {
  return templates.value.find((t) => t.id === id)?.template_name ?? '-'
}

function receiverNames(value?: string | null) {
  const ids = parseIds(value)
  if (!ids.length) return '-'
  return ids.map((id) => users.value.find((u) => u.id === id)?.real_name || `用户${id}`).join('、')
}

function channelNames(value?: string | null) {
  const ids = parseIds(value)
  if (!ids.length) return '-'
  return ids.map((id) => channels.value.find((c) => c.id === id)?.channel_name || `渠道${id}`).join('、')
}

function openDialog(row?: ReportSubscribeItem) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    template_id: row?.template_id ?? undefined,
    subscribe_name: row?.subscribe_name ?? '',
    cron_expr: row?.cron_expr ?? '0 0 8 * * ?',
    receiver_ids: parseIds(row?.receivers),
    channel_ids: parseIds(row?.channel_ids),
    enable_status: row?.enable_status ?? 1,
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    const payload = {
      template_id: form.template_id ?? null,
      subscribe_name: form.subscribe_name,
      cron_expr: form.cron_expr || null,
      receivers: form.receiver_ids.join(','),
      channel_ids: form.channel_ids.join(','),
      enable_status: form.enable_status,
    }
    if (dialog.edit && form.id) await reportApi.updateSubscription(form.id, payload)
    else await reportApi.createSubscription(payload)
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.search()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: ReportSubscribeItem) {
  await ElMessageBox.confirm(`确定删除订阅「${row.subscribe_name}」吗？`, '提示', { type: 'warning' })
  await reportApi.removeSubscription(row.id!)
  ElMessage.success('删除成功')
  await table.search()
}

async function run(row: ReportSubscribeItem) {
  await ElMessageBox.confirm(`确定立即执行订阅「${row.subscribe_name}」吗？`, '提示', { type: 'info' })
  const res = await reportApi.runSubscription(row.id!)
  ElMessage.success(`执行完成：推送 ${res.receiver_count} 人 / ${res.channel_count} 个渠道`)
  await table.search()
}

async function toggle(row: ReportSubscribeItem, value: number) {
  await reportApi.updateSubscription(row.id!, {
    template_id: row.template_id ?? null,
    subscribe_name: row.subscribe_name,
    cron_expr: row.cron_expr ?? null,
    receivers: row.receivers ?? null,
    channel_ids: row.channel_ids ?? null,
    enable_status: value,
  })
  row.enable_status = value
  ElMessage.success(value === 1 ? '已启用' : '已停用')
}

onMounted(async () => {
  await Promise.all([
    table.load(),
    reportApi.templates().then((res) => (templates.value = res)),
    listUsers({ page: 1, page_size: 100 }).then((res) => (users.value = res.items)),
    notifyApi.channels.list({ page: 1, page_size: 100 }).then((res) => (channels.value = res.items)),
  ])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>报表订阅</h2></div>

      <div class="filter-bar">
        <el-input
          v-model="table.query.subscribe_name"
          placeholder="订阅名称"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <span />
        <el-button type="primary" @click="openDialog()">新增订阅</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="subscribe_name" label="订阅名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="报表模板" min-width="160">
          <template #default="{ row }">{{ row.template_name || templateName(row.template_id) }}</template>
        </el-table-column>
        <el-table-column prop="cron_expr" label="执行周期" width="150" />
        <el-table-column label="接收人" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ receiverNames(row.receivers) }}</template>
        </el-table-column>
        <el-table-column label="推送渠道" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ channelNames(row.channel_ids) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enable_status"
              :active-value="1"
              :inactive-value="0"
              @change="(v: number) => toggle(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="最近推送" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_send_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="run(row)">立即执行</el-button>
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
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑订阅' : '新增订阅'" width="560px">
      <el-form ref="formRef" :model="form" label-width="94px">
        <el-form-item label="订阅名称" prop="subscribe_name" :rules="[{ required: true, message: '请输入订阅名称' }]">
          <el-input v-model="form.subscribe_name" placeholder="如 能耗月报-管理层订阅" />
        </el-form-item>
        <el-form-item label="报表模板" prop="template_id" :rules="[{ required: true, message: '请选择报表模板' }]">
          <el-select v-model="form.template_id" placeholder="请选择报表模板" style="width: 100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.template_name" :value="t.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行周期">
          <el-select v-model="form.cron_expr" allow-create filterable style="width: 100%">
            <el-option v-for="c in cronOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接收人">
          <el-select v-model="form.receiver_ids" multiple filterable placeholder="请选择接收人" style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="推送渠道">
          <el-select v-model="form.channel_ids" multiple placeholder="请选择推送渠道" style="width: 100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.channel_name" :value="c.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enable_status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
