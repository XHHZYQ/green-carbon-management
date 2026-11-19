<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { deviceApi, type DeviceItem } from '@/api/device'
import { dataApi, pointApi, type DeviceDataItem, type PointItem } from '@/api/point'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const devices = ref<DeviceItem[]>([])
const points = ref<PointItem[]>([])
const pointNameMap = computed(() => Object.fromEntries(points.value.map((p) => [p.id, p.point_name])))
const timeRange = ref<[string, string]>()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined

const table = useTable<DeviceDataItem>(dataApi.list, {
  device_id: undefined,
  point_id: undefined,
  data_quality: undefined,
  start_time: undefined,
  end_time: undefined,
  page_size: 50,
})

onMounted(async () => {
  const d = await deviceApi.list({ page: 1, page_size: 200 })
  devices.value = d.items
  table.load()
})

watch(() => table.query.device_id, async (id) => {
  table.query.point_id = undefined
  disposeChart()
  points.value = id ? (await pointApi.list({ device_id: id, page: 1, page_size: 200 })).items : []
})

function disposeChart() {
  chart?.dispose()
  chart = undefined
}

async function load() {
  if (timeRange.value) {
    table.query.start_time = timeRange.value[0]
    table.query.end_time = timeRange.value[1]
  } else {
    table.query.start_time = undefined
    table.query.end_time = undefined
  }
  await table.search()
  if (table.query.point_id) {
    await renderChart()
  } else {
    disposeChart()
  }
}

async function renderChart() {
  await nextTick()
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const chartData = await dataApi.list({ ...table.query, page: 1, page_size: 200 })
  const rows = [...chartData.items].reverse()
  const unit = rows.length ? rows[0].unit : ''
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: rows.map((r) => (r.collect_time || '').slice(11, 16)), boundaryGap: false },
    yAxis: { type: 'value', name: unit || '' },
    series: [{ type: 'line', smooth: true, symbol: 'none', areaStyle: {}, data: rows.map((r) => r.collect_value) }],
  })
  chart.resize()
}

function reset() {
  timeRange.value = undefined
  disposeChart()
  table.reset()
}

function onResize() {
  chart?.resize()
}
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>历史数据</h2></div>

      <div class="filter-bar">
        <el-select v-model="table.query.device_id" placeholder="选择设备" clearable filterable style="width: 200px">
          <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
        </el-select>
        <el-select
          v-model="table.query.point_id"
          placeholder="选择测点"
          clearable
          filterable
          style="width: 180px"
          @change="load"
        >
          <el-option v-for="p in points" :key="p.id" :label="p.point_name" :value="p.id" />
        </el-select>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 360px"
        />
        <el-select v-model="table.query.data_quality" placeholder="数据质量" clearable style="width: 130px">
          <el-option label="正常" value="normal" />
          <el-option label="异常" value="abnormal" />
          <el-option label="缺失" value="missing" />
          <el-option label="已补录" value="patched" />
        </el-select>
        <el-button type="primary" :disabled="!table.query.device_id" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-empty v-if="!table.query.device_id" description="请选择设备后查询" />

      <template v-else>
        <div v-if="table.query.point_id" ref="chartRef" class="chart-box" />

        <el-table v-loading="table.loading" :data="table.list" border>
          <el-table-column label="采集时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.collect_time) }}</template>
          </el-table-column>
          <el-table-column label="测点" min-width="150">
            <template #default="{ row }">{{ pointNameMap[row.point_id] || '-' }}</template>
          </el-table-column>
          <el-table-column prop="collect_value" label="采集值" width="140" />
          <el-table-column prop="unit" label="单位" width="100" />
          <el-table-column label="数据质量" width="110">
            <template #default="{ row }">
              <el-tag :type="row.data_quality === 'normal' ? 'success' : row.data_quality === 'patched' ? 'warning' : 'danger'" size="small">
                {{ { normal: '正常', abnormal: '异常', missing: '缺失', patched: '已补录' }[row.data_quality as string] || row.data_quality }}
              </el-tag>
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
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart-box {
  height: 300px;
  margin-bottom: 16px;
}
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
