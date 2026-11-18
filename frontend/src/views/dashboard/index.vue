<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'

const trendRef = ref<HTMLDivElement>()
const pieRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

// V1.0 演示数据（后续批次接入真实统计接口）
const stats = [
  { label: '在线设备数', value: '128', icon: 'Monitor', color: 'linear-gradient(135deg,#1677ff,#40a9ff)' },
  { label: '设备总数', value: '156', icon: 'Cpu', color: 'linear-gradient(135deg,#00b96b,#4bd18f)' },
  { label: '今日能耗(kWh)', value: '3,268', icon: 'Lightning', color: 'linear-gradient(135deg,#faad14,#ffd15c)' },
  { label: '今日碳排放(kg)', value: '1,864', icon: 'Cloudy', color: 'linear-gradient(135deg,#722ed1,#9b6bf0)' },
  { label: '未处理告警', value: '7', icon: 'Bell', color: 'linear-gradient(135deg,#f5222d,#ff7875)' },
]

const days = ['11-12', '11-13', '11-14', '11-15', '11-16', '11-17', '11-18']
const energySeries = [2980, 3120, 3050, 3340, 3210, 3090, 3268]

function initTrend() {
  if (!trendRef.value) return
  trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false, data: days },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '能耗',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        data: energySeries,
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

function initPie() {
  if (!pieRef.value) return
  pieChart = echarts.init(pieRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} kWh ({d}%)' },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        name: '分项能耗',
        type: 'pie',
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: [
          { value: 1320, name: '空调' },
          { value: 860, name: '照明' },
          { value: 620, name: '动力' },
          { value: 468, name: '办公' },
        ],
      },
    ],
  })
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  initTrend()
  initPie()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<template>
  <div class="dashboard">
    <div class="stat-grid">
      <div v-for="item in stats" :key="item.label" class="stat-card">
        <div>
          <div class="stat-value">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </div>
        <div class="stat-icon" :style="{ background: item.color }">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
      </div>
    </div>

    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="16">
        <div class="page-card chart-card">
          <div class="page-title"><h2>近 7 天能耗趋势</h2></div>
          <div ref="trendRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="page-card chart-card">
          <div class="page-title"><h2>分项能耗占比</h2></div>
          <div ref="pieRef" class="chart" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
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
