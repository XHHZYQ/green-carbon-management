<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { feeApi, type FeeReport } from '@/api/price'
import { formatNumber } from '@/utils/format'

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)
const year = ref(currentYear)
const loading = ref(false)
const data = ref<FeeReport | null>(null)
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value || !data.value) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 60, right: 60, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: data.value.rows.map((x) => x.month) },
    yAxis: [
      { type: 'value', name: '费用(元)' },
      { type: 'value', name: '用量(kWh)' },
    ],
    series: [
      {
        name: '费用',
        type: 'bar',
        barWidth: 20,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        data: data.value.rows.map((x) => x.fee),
      },
      {
        name: '用量',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        itemStyle: { color: '#00b96b' },
        data: data.value.rows.map((x) => x.usage),
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    data.value = await feeApi.report(year.value)
    renderChart()
  } finally {
    loading.value = false
  }
}

async function doExport() {
  const blob = await feeApi.export(year.value)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `费用报表_${year.value}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.summary.total_usage, 2) }}</div>
            <div class="stat-label">年度用量 (kWh)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.summary.total_fee, 2) }}</div>
            <div class="stat-label">年度费用 (元)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ data?.summary.avg_price }}</div>
            <div class="stat-label">平均电价 (元/kWh) · {{ data?.summary.month_count }} 个月</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title"><h2>费用报表</h2></div>
      <div class="filter-bar">
        <el-select v-model="year" style="width: 140px" @change="load">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button type="success" @click="doExport">导出报表</el-button>
      </div>

      <div ref="chartRef" class="chart" />

      <el-table v-loading="loading" :data="data?.rows ?? []" border style="margin-top: 16px">
        <el-table-column prop="month" label="月份" width="120" />
        <el-table-column label="用量 (kWh)" min-width="150">
          <template #default="{ row }">{{ formatNumber(row.usage, 2) }}</template>
        </el-table-column>
        <el-table-column label="费用 (元)" min-width="150">
          <template #default="{ row }">{{ formatNumber(row.fee, 2) }}</template>
        </el-table-column>
        <el-table-column label="平均电价 (元/kWh)" min-width="160">
          <template #default="{ row }">{{ row.avg_price }}</template>
        </el-table-column>
      </el-table>
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
