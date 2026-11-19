<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { notifyApi, type NotifyChannel } from '@/api/notify'
import { useTable } from '@/composables/useTable'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const canEdit = userStore.hasPerm('notify:message:send')

const table = useTable<NotifyChannel>(notifyApi.channels.list, { keyword: '' })

const channelTypeOptions = [
  { label: '站内消息', value: 'internal' },
  { label: '邮件', value: 'email' },
  { label: '短信', value: 'sms' },
  { label: 'Webhook', value: 'webhook' },
]

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  channel_code: '',
  channel_name: '',
  channel_type: 'internal',
  enable_status: 1,
  config_text: '{}',
})
const formRef = ref<FormInstance>()

function channelTypeLabel(value?: string | null) {
  return channelTypeOptions.find((t) => t.value === value)?.label ?? '-'
}

function openDialog(row?: NotifyChannel) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    channel_code: row?.channel_code ?? '',
    channel_name: row?.channel_name ?? '',
    channel_type: row?.channel_type ?? 'internal',
    enable_status: row?.enable_status ?? 1,
    config_text: row?.config_json ? JSON.stringify(row.config_json, null, 2) : '{}',
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  let config: Record<string, unknown> | null = null
  try {
    config = form.config_text?.trim() ? JSON.parse(form.config_text) : null
  } catch {
    ElMessage.error('配置内容不是合法的 JSON')
    return
  }
  dialog.saving = true
  try {
    const payload: Partial<NotifyChannel> = {
      channel_code: form.channel_code,
      channel_name: form.channel_name,
      channel_type: form.channel_type,
      enable_status: form.enable_status,
      config_json: config,
    }
    if (dialog.edit && form.id) await notifyApi.channels.update(form.id, payload)
    else await notifyApi.channels.create(payload)
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.load()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: NotifyChannel) {
  await ElMessageBox.confirm(`确定删除通知渠道「${row.channel_name}」吗？`, '提示', { type: 'warning' })
  await notifyApi.channels.remove(row.id!)
  ElMessage.success('删除成功')
  await table.load()
}

onMounted(() => {
  table.load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>通知渠道</h2></div>

      <div class="filter-bar">
        <el-input
          v-model="table.query.keyword"
          placeholder="渠道编码 / 名称"
          clearable
          style="width: 240px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <span />
        <el-button v-if="canEdit" type="primary" @click="openDialog()">新增</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="channel_code" label="渠道编码" width="160" />
        <el-table-column prop="channel_name" label="渠道名称" min-width="150" />
        <el-table-column label="渠道类型" width="130">
          <template #default="{ row }">{{ channelTypeLabel(row.channel_type) }}</template>
        </el-table-column>
        <el-table-column label="配置" min-width="220">
          <template #default="{ row }">
            <span class="config-text">{{ row.config_json ? JSON.stringify(row.config_json) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enable_status === 1 ? 'success' : 'info'" size="small">
              {{ row.enable_status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canEdit" link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button v-if="canEdit" link type="danger" @click="remove(row)">删除</el-button>
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

      <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑通知渠道' : '新增通知渠道'" width="560px">
        <el-form ref="formRef" :model="form" label-width="90px">
          <el-form-item label="渠道编码" prop="channel_code" :rules="[{ required: true, message: '请输入渠道编码' }]">
            <el-input v-model="form.channel_code" placeholder="如 CH_EMAIL" />
          </el-form-item>
          <el-form-item label="渠道名称" prop="channel_name" :rules="[{ required: true, message: '请输入渠道名称' }]">
            <el-input v-model="form.channel_name" placeholder="如 邮件通知" />
          </el-form-item>
          <el-form-item label="渠道类型">
            <el-select v-model="form.channel_type" style="width: 100%">
              <el-option v-for="t in channelTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="配置(JSON)">
            <el-input
              v-model="form.config_text"
              type="textarea"
              :rows="5"
              placeholder='如 {"smtp_host": "smtp.green.com", "smtp_port": 465}'
            />
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
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.config-text {
  color: #909399;
  word-break: break-all;
}
</style>
