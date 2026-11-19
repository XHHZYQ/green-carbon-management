<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { controlApi, type CommandItem, type ControlDevice } from '@/api/control'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const devices = ref<ControlDevice[]>([])
const table = useTable<CommandItem>(controlApi.commands, {
  keyword: '',
  device_id: undefined,
  status: undefined,
  source: undefined,
})
const autoRefresh = ref(false)
let timer: number | undefined

const statusMap: Record<string, { text: string; type: 'success' | 'info' | 'warning' | 'danger' | 'primary' }> = {
  pending: { text: '待下发', type: 'info' },
  sending: { text: '下发中', type: 'warning' },
  success: { text: '执行成功', type: 'success' },
  fail: { text: '执行失败', type: 'danger' },
  timeout: { text: '超时', type: 'danger' },
}
const sourceMap: Record<string, string> = {
  manual: '手动下发',
  batch: '批量下发',
  timed: '定时任务',
  scene: '场景联动',
}

onMounted(async () => {
  table.load()
  devices.value = await controlApi.points()
})
onUnmounted(() => stopAuto())

function toggleAuto(val: boolean) {
  if (val) timer = window.setInterval(() => table.load(), 3000)
  else stopAuto()
}
function stopAuto() {
  if (timer) window.clearInterval(timer)
  timer = undefined
}

const detailDialog = ref(false)
const current = ref<CommandItem>()

function openDetail(row: CommandItem) {
  current.value = row
  detailDialog.value = true
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>控制记录</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="指令编号" clearable style="width: 190px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.device_id" placeholder="设备" clearable filterable style="width: 200px" @change="table.search()">
          <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
        </el-select>
        <el-select v-model="table.query.status" placeholder="状态" clearable style="width: 130px" @change="table.search()">
          <el-option v-for="(v, k) in statusMap" :key="k" :label="v.text" :value="k" />
        </el-select>
        <el-select v-model="table.query.source" placeholder="来源" clearable style="width: 130px" @change="table.search()">
          <el-option v-for="(v, k) in sourceMap" :key="k" :label="v" :value="k" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-switch v-model="autoRefresh" style="margin-left: auto" active-text="自动刷新" @change="toggleAuto" />
        <el-button @click="table.load()">刷新</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="command_no" label="指令编号" width="190" show-overflow-tooltip />
        <el-table-column prop="device_name" label="设备" min-width="150" show-overflow-tooltip />
        <el-table-column prop="point_key" label="控制点" width="120" />
        <el-table-column prop="target_value" label="目标值" width="90" />
        <el-table-column label="来源" width="110">
          <template #default="{ row }">{{ sourceMap[row.source] || row.source || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type || 'info'" size="small">
              {{ row.status_text || statusMap[row.status]?.text || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下发时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.send_time) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.finish_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
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

    <el-dialog v-model="detailDialog" title="控制指令详情" width="560px">
      <el-descriptions v-if="current" :column="2" border>
        <el-descriptions-item label="指令编号">{{ current.command_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusMap[current.status]?.type || 'info'" size="small">
            {{ current.status_text || current.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="设备">{{ current.device_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="控制点">{{ current.point_key }}</el-descriptions-item>
        <el-descriptions-item label="目标值">{{ current.target_value }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ sourceMap[current.source || ''] || current.source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ current.priority }}</el-descriptions-item>
        <el-descriptions-item label="执行方式">{{ current.exec_mode === 'timed' ? '定时' : '立即' }}</el-descriptions-item>
        <el-descriptions-item label="下发时间">{{ formatDateTime(current.send_time) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDateTime(current.finish_time) }}</el-descriptions-item>
        <el-descriptions-item label="失败原因" :span="2">{{ current.fail_reason || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
