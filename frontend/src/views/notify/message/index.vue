<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { notifyApi, type NotifyChannel, type NotifyMessage } from '@/api/notify'
import { listUsers, type SysUser } from '@/api/system'
import { useTable } from '@/composables/useTable'
import { useUserStore } from '@/store/user'
import { formatDateTime } from '@/utils/format'

const userStore = useUserStore()
const canSend = userStore.hasPerm('notify:message:send')

const table = useTable<NotifyMessage>(notifyApi.messages, {
  msg_type: undefined,
  level: undefined,
  read_status: undefined,
  keyword: '',
})

const unread = ref(0)
const users = ref<SysUser[]>([])
const channels = ref<NotifyChannel[]>([])

const msgTypeOptions = [
  { label: '站内消息', value: 'internal' },
  { label: '邮件', value: 'email' },
  { label: '短信', value: 'sms' },
]
const levelOptions = [
  { label: '通知', value: 'info' },
  { label: '警告', value: 'warning' },
  { label: '严重', value: 'critical' },
]

const dialog = reactive({ visible: false, saving: false })
const form = reactive({
  title: '',
  content: '',
  msg_type: 'internal',
  level: 'info',
  receiver_ids: [] as number[],
  channel_ids: [] as number[],
})
const formRef = ref<FormInstance>()

function msgTypeLabel(value?: string | null) {
  return msgTypeOptions.find((t) => t.value === value)?.label ?? value ?? '-'
}

function levelLabel(value?: string | null) {
  return levelOptions.find((t) => t.value === value)?.label ?? value ?? '-'
}

function levelTagType(value?: string | null) {
  if (value === 'critical') return 'danger'
  if (value === 'warning') return 'warning'
  return 'info'
}

async function loadUnread() {
  const res = await notifyApi.unreadCount()
  unread.value = res.count
}

async function markRead(row: NotifyMessage) {
  if (row.read_status === 1) return
  await notifyApi.markRead(row.id!)
  ElMessage.success('已标记为已读')
  await Promise.all([table.load(), loadUnread()])
}

async function markAllRead() {
  const res = await notifyApi.markAllRead()
  ElMessage.success(`已将 ${res.updated} 条消息标记为已读`)
  await Promise.all([table.load(), loadUnread()])
}

function openSendDialog() {
  Object.assign(form, {
    title: '',
    content: '',
    msg_type: 'internal',
    level: 'info',
    receiver_ids: [],
    channel_ids: [],
  })
  dialog.visible = true
}

async function submitSend() {
  await formRef.value?.validate()
  if (!form.receiver_ids.length) {
    ElMessage.warning('请至少选择一个接收人')
    return
  }
  dialog.saving = true
  try {
    const res = await notifyApi.send({ ...form })
    ElMessage.success(`发送成功：消息 ${res.message_count} 条，发送记录 ${res.log_count} 条`)
    dialog.visible = false
    await Promise.all([table.load(), loadUnread()])
  } finally {
    dialog.saving = false
  }
}

async function loadOptions() {
  const [userRes, channelRes] = await Promise.all([
    listUsers({ page: 1, page_size: 100 }),
    notifyApi.channels.list({ page: 1, page_size: 100 }),
  ])
  users.value = userRes.items
  channels.value = channelRes.items
}

onMounted(async () => {
  await Promise.all([table.load(), loadUnread(), loadOptions()])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title">
        <h2>
          消息列表
          <el-tag v-if="unread" type="danger" size="small" class="unread-tag">未读 {{ unread }}</el-tag>
        </h2>
        <div>
          <el-button @click="markAllRead">一键全部已读</el-button>
          <el-button v-if="canSend" type="primary" @click="openSendDialog">发送通知</el-button>
        </div>
      </div>

      <div class="filter-bar">
        <el-select v-model="table.query.msg_type" placeholder="消息类型" clearable style="width: 150px" @change="table.search()">
          <el-option v-for="t in msgTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-select v-model="table.query.level" placeholder="级别" clearable style="width: 130px" @change="table.search()">
          <el-option v-for="t in levelOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-select v-model="table.query.read_status" placeholder="读取状态" clearable style="width: 130px" @change="table.search()">
          <el-option label="未读" :value="0" />
          <el-option label="已读" :value="1" />
        </el-select>
        <el-input
          v-model="table.query.keyword"
          placeholder="消息标题"
          clearable
          style="width: 200px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">{{ msgTypeLabel(row.msg_type) }}</template>
        </el-table-column>
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="receiver_name" label="接收人" width="120" />
        <el-table-column label="读取状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.read_status === 1 ? 'info' : 'warning'" size="small">
              {{ row.read_status === 1 ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发送时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.send_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.read_status !== 1" link type="primary" @click="markRead(row)">标记已读</el-button>
            <span v-else class="read-text">—</span>
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

    <el-dialog v-model="dialog.visible" title="发送通知" width="580px">
      <el-form ref="formRef" :model="form" label-width="90px">
        <el-form-item label="标题" prop="title" :rules="[{ required: true, message: '请输入消息标题' }]">
          <el-input v-model="form.title" placeholder="请输入消息标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="请输入消息内容" />
        </el-form-item>
        <el-form-item label="消息类型">
          <el-select v-model="form.msg_type" style="width: 100%">
            <el-option v-for="t in msgTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" style="width: 100%">
            <el-option v-for="t in levelOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接收人" prop="receiver_ids" :rules="[{ required: true, message: '请选择接收人' }]">
          <el-select v-model="form.receiver_ids" multiple filterable placeholder="请选择接收人" style="width: 100%">
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.real_name || u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="发送渠道">
          <el-select v-model="form.channel_ids" multiple placeholder="默认全部启用渠道" style="width: 100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.channel_name" :value="c.id!" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="submitSend">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.unread-tag {
  margin-left: 8px;
  vertical-align: middle;
}

.read-text {
  color: #c0c4cc;
}
</style>
