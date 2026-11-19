<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  dashboardApi,
  type CarbonOverview,
  type DashboardOverview,
  type DeviceStatus,
  type FeeQuota,
  type LatestAlarm,
  type NameValue,
  type TrendData,
} from '@/api/dashboard'
import { formatNumber } from '@/utils/format'

const loading = ref(false)
const screenMode = ref(false)

const overview = ref<DashboardOverview | null>(null)
const trend = ref<TrendData | null>(null)
const itemRatio = ref<NameValue[]>([])
const areaRank = ref<NameValue[]>([])
const carbon = ref<CarbonOverview | null>(null)
const deviceStatus = ref<DeviceStatus | null>(null)
const alarms = ref<LatestAlarm[]>([])
const feeQuota = ref<FeeQuota | null>(null)

const trendDays = ref(7)

const trendRef = ref<HTMLDivElement>()
const itemRef = ref<HTMLDivElement>()
const areaRef = ref<HTMLDivElement>()
const carbonRef = ref<HTMLDivElement>()
const deviceRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let itemChart: echarts.ECharts | null = null
let areaChart: echarts.ECharts | null = null
let carbonChart: echarts.ECharts | null = null
let deviceChart: echarts.ECharts | null = null
let timer: number | null = null

const levelMap: Record<string, { text: string; type: 'danger' | 'warning' | 'info' | 'success' }> = {
  critical: { text: '紧急', type: 'danger' },
  major: { text: '重要', type: 'warning' },
  minor: { text: '次要', type: 'info' },
  info: { text: '提示', type: 'success' },
}

const axisColor = computed(() => (screenMode.value ? '#9db6d8' : '#6b7a90'))

function chartTextColor() {
  return screenMode.value ? '#c7d6ea' : '#33445c'
}

function initTrend() {
  if (!trendRef.value || !trend.value) return
  trendChart = trendChart ?? echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: chartTextColor() } },
    grid: { left: 60, right: 60, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: trend.value.dates, axisLabel: { color: axisColor.value } },
    yAxis: [
      { type: 'value', name: 'kWh', axisLabel: { color: axisColor.value } },
      { type: 'value', name: 'tCO2e', axisLabel: { color: axisColor.value } },
    ],
    series: [
      {
        name: '用电量',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        itemStyle: { color: '#1E6FFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(30,111,255,0.35)' },
            { offset: 1, color: 'rgba(30,111,255,0.02)' },
          ]),
        },
        data: trend.value.energy,
      },
      {
        name: '碳排',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        symbolSize: 7,
        itemStyle: { color: '#00b96b' },
        data: trend.value.carbon,
      },
    ],
  })
}

function initItem() {
  if (!itemRef.value) return
  itemChart = itemChart ?? echarts.init(itemRef.value)
  itemChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} kWh ({d}%)' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: chartTextColor() } },
    series: [
      {
        name: '分项用电',
        type: 'pie',
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
        label: { show: false },
        data: itemRatio.value,
      },
    ],
  })
}

function initArea() {
  if (!areaRef.value) return
  areaChart = areaChart ?? echarts.init(areaRef.value)
  const names = areaRank.value.map((x) => x.name)
  const values = areaRank.value.map((x) => x.value)
  areaChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 30, top: 20, bottom: 30 },
    xAxis: { type: 'value', axisLabel: { color: axisColor.value } },
    yAxis: { type: 'category', data: names.slice().reverse(), axisLabel: { color: axisColor.value } },
    series: [
      {
        name: '用电量',
        type: 'bar',
        barWidth: 14,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#40a9ff' },
            { offset: 1, color: '#1E6FFF' },
          ]),
        },
        data: values.slice().reverse(),
      },
    ],
  })
}

function initCarbon() {
  if (!carbonRef.value || !carbon.value) return
  carbonChart = carbonChart ?? echarts.init(carbonRef.value)
  carbonChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} tCO2e ({d}%)' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: chartTextColor() } },
    series: [
      {
        name: '排放范围',
        type: 'pie',
        radius: ['48%', '70%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
        label: { show: false },
        data: carbon.value.scopes,
      },
    ],
  })
}

function initDevice() {
  if (!deviceRef.value || !deviceStatus.value) return
  deviceChart = deviceChart ?? echarts.init(deviceRef.value)
  deviceChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 台 ({d}%)' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: chartTextColor() } },
    series: [
      {
        name: '设备在线状态',
        type: 'pie',
        radius: ['55%', '75%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
        label: { show: true, color: chartTextColor(), formatter: '{b}\n{c}' },
        data: deviceStatus.value.online,
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    const [ov, tr, it, ar, cb, ds, al, fq] = await Promise.all([
      dashboardApi.overview(),
      dashboardApi.energyTrend(trendDays.value),
      dashboardApi.energyItemRatio(),
      dashboardApi.areaRank(8),
      dashboardApi.carbonOverview(),
      dashboardApi.deviceStatus(),
      dashboardApi.latestAlarms(10),
      dashboardApi.feeQuota(),
    ])
    overview.value = ov
    trend.value = tr
    itemRatio.value = it
    areaRank.value = ar
    carbon.value = cb
    deviceStatus.value = ds
    alarms.value = al
    feeQuota.value = fq
    initTrend()
    initItem()
    initArea()
    initCarbon()
    initDevice()
  } finally {
    loading.value = false
  }
}

function handleResize() {
  trendChart?.resize()
  itemChart?.resize()
  areaChart?.resize()
  carbonChart?.resize()
  deviceChart?.resize()
}

async function toggleScreen() {
  screenMode.value = !screenMode.value
  try {
    if (screenMode.value) await document.documentElement.requestFullscreen()
    else if (document.fullscreenElement) await document.exitFullscreen()
  } catch {
    // 忽略全屏 API 异常（浏览器策略限制）
  }
  setTimeout(handleResize, 300)
}

function onFullscreenChange() {
  if (!document.fullscreenElement) screenMode.value = false
  setTimeout(handleResize, 300)
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
  window.addEventListener('resize', handleResize)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  trendChart?.dispose()
  itemChart?.dispose()
  areaChart?.dispose()
  carbonChart?.dispose()
  deviceChart?.dispose()
})
</script>

<template>
  <div v-loading="loading" class="page-container dashboard" :class="{ 'screen-mode': screenMode }">
    <div class="dash-header">
      <h2>绿色低碳智慧管控 · 数据驾驶舱</h2>
      <div class="dash-actions">
        <span class="refresh-tip">每 30 秒自动刷新</span>
        <el-button size="small" @click="load">刷新</el-button>
        <el-button size="small" type="primary" @click="toggleScreen">
          {{ screenMode ? '退出大屏' : '大屏模式' }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="card in [
        { label: '设备总数', value: overview?.device_total, unit: '台' },
        { label: '在线设备', value: overview?.device_online, unit: '台', extra: `在线率 ${overview?.online_rate ?? 0}%` },
        { label: '今日能耗', value: overview?.today_energy, unit: 'kWh' },
        { label: '本月能耗', value: overview?.month_energy, unit: 'kWh' },
        { label: '今日碳排', value: overview?.today_carbon, unit: 'tCO2e' },
        { label: '本月费用', value: overview?.month_fee, unit: '元' },
        { label: '未处理告警', value: overview?.pending_alarm, unit: '条' },
        { label: '定额完成率', value: overview?.quota_rate, unit: '%', extra: `超定额 ${overview?.quota_exceed ?? 0} 项` },
      ]" :key="card.label" :xs="12" :sm="12" :md="6" :lg="3">
        <div class="stat-card metric">
          <div>
            <div class="stat-value">{{ formatNumber(card.value, card.unit === '%' ? 2 : 0) }}</div>
            <div class="stat-label">{{ card.label }}<span v-if="card.unit"> ({{ card.unit }})</span></div>
            <div class="stat-extra">{{ card.extra || '' }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="16">
        <div class="page-card chart-card">
          <div class="page-title">
            <h2>能耗与碳排趋势</h2>
            <el-select v-model="trendDays" style="width: 120px" @change="load">
              <el-option label="近 7 天" :value="7" />
              <el-option label="近 30 天" :value="30" />
            </el-select>
          </div>
          <div ref="trendRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="page-card chart-card">
          <div class="page-title"><h2>分项用电占比</h2></div>
          <div ref="itemRef" class="chart" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="12">
        <div class="page-card chart-card">
          <div class="page-title"><h2>区域用电排名</h2></div>
          <div ref="areaRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="6">
        <div class="page-card chart-card">
          <div class="page-title"><h2>碳排范围构成</h2></div>
          <div ref="carbonRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="6">
        <div class="page-card chart-card">
          <div class="page-title"><h2>设备在线状态</h2></div>
          <div ref="deviceRef" class="chart" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="16">
        <div class="page-card">
          <div class="page-title"><h2>最新告警</h2></div>
          <el-table :data="alarms" size="small" max-height="320">
            <el-table-column prop="alarm_time" label="时间" width="170" />
            <el-table-column prop="device_name" label="设备" min-width="130" show-overflow-tooltip />
            <el-table-column prop="content" label="告警内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="alarm_level" label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="levelMap[row.alarm_level]?.type ?? 'info'" size="small" effect="dark">
                  {{ levelMap[row.alarm_level]?.text ?? row.alarm_level }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="page-card chart-card">
          <div class="page-title"><h2>费用与定额</h2></div>
          <div class="fee-quota">
            <div class="fq-item">
              <div class="fq-value">{{ formatNumber(feeQuota?.month_fee, 2) }}</div>
              <div class="fq-label">本月费用 (元)</div>
            </div>
            <div class="fq-item">
              <div class="fq-value">
                {{ feeQuota && feeQuota.fee_mom > 0 ? '↑' : feeQuota && feeQuota.fee_mom < 0 ? '↓' : '' }}{{ Math.abs(feeQuota?.fee_mom ?? 0) }}%
              </div>
              <div class="fq-label">费用环比</div>
            </div>
            <div class="fq-item">
              <div class="fq-value">{{ feeQuota?.quota_rate ?? 0 }}%</div>
              <div class="fq-label">定额完成率</div>
            </div>
            <div class="fq-item">
              <div class="fq-value">{{ feeQuota?.quota_warning ?? 0 }} / {{ feeQuota?.quota_exceed ?? 0 }}</div>
              <div class="fq-label">预警 / 超定额 (项)</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  min-height: 100%;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
  }
}

.dash-actions {
  display: flex;
  align-items: center;
  gap: 10px;

  .refresh-tip {
    font-size: 12px;
    color: #8a97a8;
  }
}

.metric {
  margin-bottom: 16px;
  padding: 14px 16px;

  .stat-value {
    font-size: 22px;
  }
}

.stat-extra {
  margin-top: 4px;
  min-height: 16px;
  line-height: 16px;
  font-size: 12px;
  color: #8a97a8;
}

.chart {
  width: 100%;
  height: 300px;
}

.chart-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  .chart {
    flex: 1;
    min-height: 0;
    height: auto;
  }
}

.fee-quota {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  align-content: center;

  .fq-item {
    background: rgba(30, 111, 255, 0.06);
    border-radius: 8px;
    padding: 16px 12px;
    text-align: center;
  }

  .fq-value {
    font-size: 22px;
    font-weight: 700;
    color: #1e6fff;
  }

  .fq-label {
    margin-top: 6px;
    font-size: 12px;
    color: #8a97a8;
  }
}

.row-gap {
  margin-top: 16px;
}

// ============ 大屏模式（深色） ============
.screen-mode {
  padding: 20px;
  background: radial-gradient(circle at 50% 0%, #0b2547 0%, #05142b 60%, #030c1a 100%);
  min-height: 100vh;

  .dash-header h2 {
    color: #ffffff;
    text-shadow: 0 0 12px rgba(30, 111, 255, 0.8);
  }

  .refresh-tip {
    color: #7f9ac0;
  }

  :deep(.page-card),
  :deep(.stat-card) {
    background: rgba(13, 40, 78, 0.75);
    border: 1px solid rgba(64, 169, 255, 0.25);
    box-shadow: 0 0 18px rgba(30, 111, 255, 0.15) inset;
  }

  :deep(.page-title h2) {
    color: #e6f0ff;
  }

  :deep(.stat-value) {
    color: #ffffff;
  }

  :deep(.stat-label),
  :deep(.stat-extra),
  :deep(.fq-label) {
    color: #9db6d8;
  }

  .fq-item {
    background: rgba(30, 111, 255, 0.15);
  }

  .fq-value {
    color: #4d9bff;
  }

  :deep(.el-table) {
    background: transparent;
    color: #c7d6ea;

    tr,
    th.el-table__cell,
    td.el-table__cell {
      background: transparent;
      color: #c7d6ea;
      border-color: rgba(64, 169, 255, 0.15);
    }

    th.el-table__cell {
      color: #9db6d8;
    }
  }
}
</style>
