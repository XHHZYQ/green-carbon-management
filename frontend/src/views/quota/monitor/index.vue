<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { quotaApi, type QuotaMonitorItem } from '@/api/quota'
import { useTable } from '@/composables/useTable'
import { formatNumber } from '@/utils/format'

const table = useTable<QuotaMonitorItem>(quotaApi.monitors, {
  page_size: 10,
  warn_status: undefined,
  period_value: undefined,
})

const refreshPeriod = ref('')
const refreshing = ref(false)

const warnStatusOptions = [
  { label: '正常', value: 'normal' },
  { label: '预警', value: 'warning' },
  { label: '超标', value: 'exceed' },
]

const warnStatusMap: Record<string, { label: string; type: 'success' | 'warning' | 'danger' }> = {
  normal: { label: '正常', type: 'success' },
  warning: { label: '预警', type: 'warning' },
  exceed: { label: '超标', type: 'danger' },
}

function warnLabel(status?: string | null) {
  return status ? warnStatusMap[status]?.label ?? status : '-'
}

function warnTagType(status?: string | null) {
  return status ? warnStatusMap[status]?.type ?? 'info' : 'info'
}

function progressStatus(status?: string | null) {
  if (status === 'exceed') return 'exception'
  if (status === 'warning') return 'warning'
  return 'success'
}

function progressColor(status?: string | null) {
  if (status === 'exceed') return '#f5222d'
  if (status === 'warning') return '#faad14'
  return '#00b96b'
}

function rowClassName({ row }: { row: QuotaMonitorItem }) {
  return row.warn_status === 'exceed' ? 'row-exceed' : ''
}

async function doRefresh() {
  refreshing.value = true
  try {
    const res = await quotaApi.refresh({ period_value: refreshPeriod.value || null })
    ElMessage.success(
      `刷新完成：监控 ${res.monitor_count} 条，超标 ${res.exceed_count} 条，预警通知 ${res.notified} 条`,
    )
    await table.load()
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  table.load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title">
        <h2>定额监控</h2>
        <div style="display: flex; gap: 12px; align-items: center">
          <el-date-picker
            v-model="refreshPeriod"
            type="month"
            value-format="YYYY-MM"
            placeholder="刷新周期（默认当月）"
            style="width: 200px"
          />
          <el-button type="primary" :loading="refreshing" @click="doRefresh">刷新监控</el-button>
        </div>
      </div>

      <div class="filter-bar">
        <el-date-picker
          v-model="table.query.period_value"
          type="month"
          value-format="YYYY-MM"
          placeholder="统计周期"
          clearable
          style="width: 180px"
          @change="table.search()"
        />
        <el-select v-model="table.query.warn_status" placeholder="预警状态" clearable style="width: 150px" @change="table.search()">
          <el-option v-for="t in warnStatusOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border :row-class-name="rowClassName">
        <el-table-column prop="quota_name" label="定额名称" min-width="200" />
        <el-table-column prop="period_value" label="统计周期" width="110" />
        <el-table-column label="实际值" width="140">
          <template #default="{ row }">{{ formatNumber(row.actual_value, 2) }} {{ row.unit }}</template>
        </el-table-column>
        <el-table-column label="定额值" width="140">
          <template #default="{ row }">{{ formatNumber(row.quota_value, 2) }} {{ row.unit }}</template>
        </el-table-column>
        <el-table-column label="完成率" min-width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(Number(row.complete_rate) || 0, 100)"
              :status="progressStatus(row.warn_status)"
              :color="progressColor(row.warn_status)"
              :format="() => `${formatNumber(row.complete_rate, 2)}%`"
            />
          </template>
        </el-table-column>
        <el-table-column label="偏差" width="110">
          <template #default="{ row }">{{ formatNumber(row.deviation, 2) }}%</template>
        </el-table-column>
        <el-table-column label="预警状态" width="100">
          <template #default="{ row }">
            <el-tag :type="warnTagType(row.warn_status)" size="small">{{ warnLabel(row.warn_status) }}</el-tag>
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
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

:deep(.row-exceed) {
  background-color: #fff1f0;
}
</style>
