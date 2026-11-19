<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { energyApi, type EnergyOverview } from '@/api/energy'
import { formatNumber } from '@/utils/format'

const data = ref<EnergyOverview | null>(null)
const loading = ref(false)

const trendRef = ref<HTMLDivElement>()
const typeRef = ref<HTMLDivElement>()
const rankRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let rankChart: echarts.ECharts | null = null

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
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false, data: data.value.trend.dates },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '用电量',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: data.value.trend.values,
        itemStyle: { color: '#1677ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(22,119,255,0.35)' },
            { offset: 1, color: 'rgba(22,119,255,0.02)' },
          ]),
        },
      },
    ],
  })
}

function initType() {
  if (!typeRef.value || !data.value) return
  typeChart = typeChart ?? echarts.init(typeRef.value)
  typeChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        name: '能源类型构成',
        type: 'pie',
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: data.value.type_ratio,
      },
    ],
  })
}

function initRank() {
  if (!rankRef.value || !data.value) return
  rankChart = rankChart ?? echarts.init(rankRef.value)
  const list = [...data.value.area_rank].reverse()
  rankChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 90, right: 24, top: 20, bottom: 20 },
    xAxis: { type: 'value', name: 'kWh' },
    yAxis: { type: 'category', data: list.map((x) => x.name) },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        itemStyle: { color: '#1677ff', borderRadius: [0, 4, 4, 0] },
        data: list.map((x) => x.value),
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    data.value = await energyApi.overview()
    initTrend()
    initType()
    initRank()
  } finally {
    loading.value = false
  }
}

function handleResize() {
  trendChart?.resize()
  typeChart?.resize()
  rankChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  typeChart?.dispose()
  rankChart?.dispose()
})
</script>

<template>
  <div v-loading="loading" class="page-container">
    <div class="stat-grid">
      <div class="stat-card">
        <div>
          <div class="stat-value">{{ formatNumber(data?.cards.month_energy, 2) }}</div>
          <div class="stat-label">本月能耗 (kWh)</div>
          <div class="stat-extra">环比 {{ rateText(data?.cards.mom_rate) }} / 同比 {{ rateText(data?.cards.yoy_rate) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div>
          <div class="stat-value">{{ formatNumber(data?.cards.month_fee, 2) }}</div>
          <div class="stat-label">本月费用 (元)</div>
        </div>
      </div>
      <div class="stat-card">
        <div>
          <div class="stat-value">{{ formatNumber(data?.cards.month_carbon, 2) }}</div>
          <div class="stat-label">本月碳排放 (tCO2e)</div>
        </div>
      </div>
      <div class="stat-card">
        <div>
          <div class="stat-value">{{ formatNumber(data?.cards.today_energy, 2) }}</div>
          <div class="stat-label">今日能耗 (kWh)</div>
        </div>
      </div>
    </div>

    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="16">
        <div class="page-card chart-card">
          <div class="page-title"><h2>近 30 天能耗趋势</h2></div>
          <div ref="trendRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="page-card chart-card">
          <div class="page-title"><h2>能源类型构成</h2></div>
          <div ref="typeRef" class="chart" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <div class="page-card chart-card" style="height: 320px">
          <div class="page-title"><h2>区域能耗排名</h2></div>
          <div ref="rankRef" class="chart" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-extra {
  margin-top: 4px;
  font-size: 12px;
  color: #8a97a8;
}

.chart-row {
  margin-top: 16px;
}

.chart-card {
  height: 380px;
  display: flex;
  flex-direction: column;
}

.chart {
  flex: 1;
  width: 100%;
  min-height: 0;
}
</style>
