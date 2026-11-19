<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { feeApi, type FeeCompare, type FeeStat } from '@/api/price'
import { formatNumber } from '@/utils/format'

const dimOptions = [
  { label: '按分时', value: 'period' },
  { label: '按月', value: 'month' },
  { label: '按区域', value: 'area' },
]

const dim = ref('period')
const loading = ref(false)
const stat = ref<FeeStat | null>(null)
const compare = ref<FeeCompare | null>(null)

const statRef = ref<HTMLDivElement>()
const compareRef = ref<HTMLDivElement>()
let statChart: echarts.ECharts | null = null
let compareChart: echarts.ECharts | null = null

function rateText(v?: number | null) {
  if (v === null || v === undefined) return '—'
  const arrow = v > 0 ? '↑' : v < 0 ? '↓' : ''
  return `${arrow}${Math.abs(v)}%`
}

function renderStat() {
  if (!statRef.value || !stat.value) return
  statChart = statChart ?? echarts.init(statRef.value)
  statChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 60, right: 60, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: stat.value.items.map((x) => x.name), axisLabel: { interval: 0, rotate: 15 } },
    yAxis: [
      { type: 'value', name: '费用(元)' },
      { type: 'value', name: '用量' },
    ],
    series: [
      {
        name: '费用',
        type: 'bar',
        barWidth: 26,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        data: stat.value.items.map((x) => x.fee),
      },
      {
        name: '用量',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        itemStyle: { color: '#00b96b' },
        data: stat.value.items.map((x) => x.usage),
      },
    ],
  })
}

function renderCompare() {
  if (!compareRef.value || !compare.value) return
  compareChart = compareChart ?? echarts.init(compareRef.value)
  compareChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 60, right: 24, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: compare.value.period_compare.map((x) => x.name) },
    yAxis: { type: 'value', name: '费用(元)' },
    series: [
      {
        name: '本月',
        type: 'bar',
        barWidth: 22,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        data: compare.value.period_compare.map((x) => x.current),
      },
      {
        name: '上月',
        type: 'bar',
        barWidth: 22,
        itemStyle: { color: '#8bbbff', borderRadius: [4, 4, 0, 0] },
        data: compare.value.period_compare.map((x) => x.last),
      },
    ],
  })
}

async function loadStat() {
  loading.value = true
  try {
    stat.value = await feeApi.stat(dim.value)
    renderStat()
  } finally {
    loading.value = false
  }
}

async function loadCompare() {
  compare.value = await feeApi.compare()
  renderCompare()
}

function handleResize() {
  statChart?.resize()
  compareChart?.resize()
}

onMounted(async () => {
  await Promise.all([loadStat(), loadCompare()])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  statChart?.dispose()
  compareChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(stat?.summary.total_usage, 2) }}</div>
            <div class="stat-label">累计用量 (kWh)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(stat?.summary.total_fee, 2) }}</div>
            <div class="stat-label">累计费用 (元)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ stat?.summary.avg_price }}</div>
            <div class="stat-label">平均电价 (元/kWh)</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title"><h2>费用统计</h2></div>
      <div class="filter-bar">
        <el-radio-group v-model="dim" @change="loadStat">
          <el-radio-button v-for="d in dimOptions" :key="d.value" :value="d.value">{{ d.label }}</el-radio-button>
        </el-radio-group>
      </div>
      <div ref="statRef" class="chart" />
      <el-table v-loading="loading" :data="stat?.items ?? []" border style="margin-top: 16px">
        <el-table-column prop="name" label="维度" min-width="140" />
        <el-table-column label="用量 (kWh)" min-width="140">
          <template #default="{ row }">{{ formatNumber(row.usage, 2) }}</template>
        </el-table-column>
        <el-table-column label="费用 (元)" min-width="140">
          <template #default="{ row }">{{ formatNumber(row.fee, 2) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-card row-gap">
      <div class="page-title"><h2>费用对比</h2></div>
      <el-row :gutter="16">
        <el-col :xs="24" :lg="8">
          <div class="stat-card">
            <div>
              <div class="stat-value">{{ formatNumber(compare?.current.fee, 2) }}</div>
              <div class="stat-label">本月费用 (元) · {{ compare?.current.month }}</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :lg="8">
          <div class="stat-card">
            <div>
              <div class="stat-value">{{ rateText(compare?.mom.rate) }}</div>
              <div class="stat-label">环比 · 上月 {{ formatNumber(compare?.mom.fee, 2) }}</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :lg="8">
          <div class="stat-card">
            <div>
              <div class="stat-value">{{ rateText(compare?.yoy.rate) }}</div>
              <div class="stat-label">同比 · 去年 {{ formatNumber(compare?.yoy.fee, 2) }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
      <div ref="compareRef" class="chart" style="margin-top: 16px" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart {
  width: 100%;
  height: 300px;
}

.row-gap {
  margin-top: 16px;
}
</style>
