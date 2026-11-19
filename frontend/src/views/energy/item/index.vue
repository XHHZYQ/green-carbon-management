<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { energyApi, type EnergyAnalysisItem, type PeakValleyItem } from '@/api/energy'
import { formatNumber } from '@/utils/format'

const query = reactive({ range: [] as string[] })
const loading = ref(false)
const itemList = ref<EnergyAnalysisItem[]>([])
const peakList = ref<PeakValleyItem[]>([])

const pieRef = ref<HTMLDivElement>()
const barRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

function params() {
  return { start: query.range[0] || undefined, end: query.range[1] || undefined }
}

function renderPie() {
  if (!pieRef.value) return
  pieChart = pieChart ?? echarts.init(pieRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} kWh ({d}%)' },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        name: '分项占比',
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%' },
        data: itemList.value.map((x) => ({ name: x.name, value: x.value })),
      },
    ],
  })
}

function renderBar() {
  if (!barRef.value) return
  barChart = barChart ?? echarts.init(barRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 60, right: 24, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: peakList.value.map((x) => x.period_name) },
    yAxis: { type: 'value', name: '费用 (元)' },
    series: [
      {
        name: '费用',
        type: 'bar',
        barWidth: 30,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        data: peakList.value.map((x) => x.fee),
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    const [items, peaks] = await Promise.all([energyApi.itemRatio(params()), energyApi.peakValley(params())])
    itemList.value = items
    peakList.value = peaks
    renderPie()
    renderBar()
  } finally {
    loading.value = false
  }
}

function reset() {
  query.range = []
  load()
}

async function doExport() {
  const blob = await energyApi.export(params())
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `能耗数据_${Date.now()}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

function handleResize() {
  pieChart?.resize()
  barChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  barChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>分项计量</h2></div>
      <div class="filter-bar">
        <el-date-picker
          v-model="query.range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <el-button type="success" @click="doExport">导出</el-button>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <div ref="pieRef" class="chart" />
        </el-col>
        <el-col :xs="24" :lg="12">
          <div ref="barRef" class="chart" />
        </el-col>
      </el-row>
    </div>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="12">
        <div class="page-card">
          <div class="page-title"><h2>分项用量占比</h2></div>
          <el-table v-loading="loading" :data="itemList" border>
            <el-table-column prop="name" label="分项" min-width="120" />
            <el-table-column label="用量 (kWh)" min-width="130">
              <template #default="{ row }">{{ formatNumber(row.value, 2) }}</template>
            </el-table-column>
            <el-table-column label="占比" width="100">
              <template #default="{ row }">{{ row.ratio }}%</template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="page-card">
          <div class="page-title"><h2>峰谷用电分析</h2></div>
          <el-table v-loading="loading" :data="peakList" border>
            <el-table-column prop="period_name" label="时段" width="90" />
            <el-table-column label="用电量 (kWh)" min-width="120">
              <template #default="{ row }">{{ formatNumber(row.usage, 2) }}</template>
            </el-table-column>
            <el-table-column label="电价" width="100">
              <template #default="{ row }">{{ row.price }}</template>
            </el-table-column>
            <el-table-column label="费用 (元)" min-width="120">
              <template #default="{ row }">{{ formatNumber(row.fee, 2) }}</template>
            </el-table-column>
            <el-table-column label="费用占比" width="100">
              <template #default="{ row }">{{ row.fee_ratio }}%</template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.chart {
  width: 100%;
  height: 320px;
}

.row-gap {
  margin-top: 16px;
}
</style>
