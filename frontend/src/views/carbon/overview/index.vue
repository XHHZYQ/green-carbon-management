<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { carbonApi, type CarbonOverview } from '@/api/carbon'
import { formatNumber } from '@/utils/format'

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)
const year = ref(currentYear)
const loading = ref(false)
const data = ref<CarbonOverview | null>(null)

const trendRef = ref<HTMLDivElement>()
const typeRef = ref<HTMLDivElement>()
const scopeRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let scopeChart: echarts.ECharts | null = null

function rateText(v?: number | null) {
  if (v === null || v === undefined) return '—'
  const arrow = v > 0 ? '↑' : v < 0 ? '↓' : ''
  return `${arrow}${Math.abs(v)}%`
}

function initTrend() {
  if (!trendRef.value || !data.value) return
  trendChart = trendChart ?? echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 24, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: data.value.trend.months, axisLabel: { rotate: 20 } },
    yAxis: { type: 'value', name: 'tCO2e' },
    series: [
      {
        name: '碳排放',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        itemStyle: { color: '#00b96b' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0,185,107,0.35)' },
            { offset: 1, color: 'rgba(0,185,107,0.02)' },
          ]),
        },
        data: data.value.trend.values,
      },
    ],
  })
}

function initPie(target: 'type' | 'scope') {
  const el = target === 'type' ? typeRef.value : scopeRef.value
  if (!el || !data.value) return
  const chart = target === 'type' ? (typeChart = typeChart ?? echarts.init(el)) : (scopeChart = scopeChart ?? echarts.init(el))
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} tCO2e ({d}%)' },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        name: target === 'type' ? '能源类型' : '排放范围',
        type: 'pie',
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: target === 'type' ? data.value.type_ratio : data.value.scope_ratio,
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    data.value = await carbonApi.overview(year.value)
    initTrend()
    initPie('type')
    initPie('scope')
  } finally {
    loading.value = false
  }
}

function handleResize() {
  trendChart?.resize()
  typeChart?.resize()
  scopeChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  typeChart?.dispose()
  scopeChart?.dispose()
})
</script>

<template>
  <div v-loading="loading" class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.cards.total, 2) }}</div>
            <div class="stat-label">{{ data?.cards.year }} 年总排放 (tCO2e)</div>
            <div class="stat-extra">同比 {{ rateText(data?.cards.yoy_rate) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.cards.scope1, 2) }}</div>
            <div class="stat-label">范围一 (tCO2e)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.cards.scope2, 2) }}</div>
            <div class="stat-label">范围二 (tCO2e)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(data?.cards.scope3, 2) }}</div>
            <div class="stat-label">范围三 (tCO2e)</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title">
        <h2>碳排放趋势</h2>
        <el-select v-model="year" style="width: 140px" @change="load">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>
      </div>
      <div ref="trendRef" class="chart" />
    </div>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="12">
        <div class="page-card chart-card">
          <div class="page-title"><h2>能源类型排放构成</h2></div>
          <div ref="typeRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="page-card chart-card">
          <div class="page-title"><h2>排放范围构成</h2></div>
          <div ref="scopeRef" class="chart" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.stat-extra {
  margin-top: 4px;
  font-size: 12px;
  color: #8a97a8;
}

.chart {
  width: 100%;
  height: 300px;
}

.chart-card {
  height: 360px;
  display: flex;
  flex-direction: column;

  .chart {
    flex: 1;
    min-height: 0;
    height: auto;
  }
}

.row-gap {
  margin-top: 16px;
}
</style>
