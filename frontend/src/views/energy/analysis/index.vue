<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { energyApi, type EnergyAnalysisItem } from '@/api/energy'
import { formatNumber } from '@/utils/format'

const dimOptions = [
  { label: '按区域', value: 'area' },
  { label: '按分项', value: 'item' },
  { label: '按设备', value: 'device' },
]

const query = reactive({
  dim: 'area',
  range: [] as string[],
})

const loading = ref(false)
const list = ref<EnergyAnalysisItem[]>([])
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function params() {
  return {
    dim: query.dim,
    start: query.range[0] || undefined,
    end: query.range[1] || undefined,
    limit: 10,
  }
}

function renderChart() {
  if (!chartRef.value) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 60, right: 24, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: list.value.map((x) => x.name), axisLabel: { interval: 0, rotate: 20 } },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        type: 'bar',
        barWidth: 22,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        data: list.value.map((x) => x.value),
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    list.value = await energyApi.rank(params())
    renderChart()
  } finally {
    loading.value = false
  }
}

function reset() {
  query.dim = 'area'
  query.range = []
  load()
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
    <div class="page-card">
      <div class="page-title"><h2>能耗分析</h2></div>

      <div class="filter-bar">
        <el-radio-group v-model="query.dim" @change="load">
          <el-radio-button v-for="d in dimOptions" :key="d.value" :value="d.value">{{ d.label }}</el-radio-button>
        </el-radio-group>
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
      </div>

      <div ref="chartRef" class="chart" />

      <el-table v-loading="loading" :data="list" border style="margin-top: 16px">
        <el-table-column prop="rank" label="排名" width="80" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="能耗值 (kWh)" min-width="140">
          <template #default="{ row }">{{ formatNumber(row.value, 2) }}</template>
        </el-table-column>
        <el-table-column label="占比" width="120">
          <template #default="{ row }">{{ row.ratio }}%</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart {
  width: 100%;
  height: 320px;
}
</style>
