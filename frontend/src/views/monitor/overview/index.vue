<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { areaApi, type AreaNode } from '@/api/device'
import { monitorApi, type CurvePoint, type RealtimeDevice } from '@/api/monitor'

const areaOptions = ref<{ id: number; name: string }[]>([])
const areaId = ref<number>()
const keyword = ref('')
const interval = ref(3)
const loading = ref(false)
const devices = ref<RealtimeDevice[]>([])
const activeId = ref<number>()
const activePointId = ref<number>()
const curveRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined
let timer: number | undefined

const activeDevice = computed(() => devices.value.find((d) => d.device_id === activeId.value))
const onlineCount = computed(() => devices.value.filter((d) => d.online_status === 'online').length)

function flatten(nodes: AreaNode[], depth = 0, out: { id: number; name: string }[] = []) {
  for (const n of nodes) {
    out.push({ id: n.id, name: `${'　'.repeat(depth)}${n.area_name}` })
    if (n.children?.length) flatten(n.children, depth + 1, out)
  }
  return out
}

async function fetchRealtime() {
  loading.value = true
  try {
    devices.value = await monitorApi.realtime({ area_id: areaId.value, keyword: keyword.value || undefined })
    if (activeId.value && !devices.value.some((d) => d.device_id === activeId.value)) {
      selectDevice(devices.value[0])
    } else if (!activeId.value && devices.value.length) {
      selectDevice(devices.value[0])
    } else {
      await renderCurve()
    }
  } finally {
    loading.value = false
  }
}

function selectDevice(d?: RealtimeDevice) {
  activeId.value = d?.device_id
  activePointId.value = d?.points[0]?.point_id
  renderCurve()
}

async function renderCurve() {
  await nextTick()
  if (!activePointId.value || !curveRef.value) {
    chart?.clear()
    return
  }
  const rows = await monitorApi.curve({ point_id: activePointId.value, hours: 1 })
  drawCurve(rows)
}

function drawCurve(rows: CurvePoint[]) {
  if (!curveRef.value) return
  if (!chart) chart = echarts.init(curveRef.value)
  const point = activeDevice.value?.points.find((p) => p.point_id === activePointId.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: rows.map((r) => (r.collect_time || '').slice(11, 16)), boundaryGap: false },
    yAxis: { type: 'value', name: point?.unit || '' },
    series: [{ type: 'line', smooth: true, symbol: 'none', areaStyle: {}, data: rows.map((r) => r.collect_value) }],
  })
  chart.resize()
}

function restartTimer() {
  stopTimer()
  timer = window.setInterval(async () => {
    await fetchRealtime()
  }, interval.value * 1000)
}
function stopTimer() {
  if (timer) window.clearInterval(timer)
  timer = undefined
}

watch(interval, () => restartTimer())

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  const tree = await areaApi.tree()
  areaOptions.value = flatten(tree)
  await fetchRealtime()
  restartTimer()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>实时监控总览</h2></div>

      <div class="filter-bar">
        <el-select v-model="areaId" placeholder="全部区域" clearable filterable style="width: 200px" @change="fetchRealtime">
          <el-option v-for="a in areaOptions" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
        <el-input v-model="keyword" placeholder="设备名称" clearable style="width: 180px" @keyup.enter="fetchRealtime" />
        <el-select v-model="interval" style="width: 120px">
          <el-option label="1 秒刷新" :value="1" />
          <el-option label="3 秒刷新" :value="3" />
          <el-option label="5 秒刷新" :value="5" />
        </el-select>
        <el-button type="primary" @click="fetchRealtime">立即刷新</el-button>
        <div class="stat">
          <el-tag type="success" size="small">在线 {{ onlineCount }}</el-tag>
          <el-tag type="info" size="small">共 {{ devices.length }}</el-tag>
        </div>
      </div>

      <div v-loading="loading" class="device-grid">
        <div
          v-for="d in devices"
          :key="d.device_id"
          class="device-card"
          :class="{ active: d.device_id === activeId }"
          @click="selectDevice(d)"
        >
          <div class="dc-head">
            <span class="dc-name">{{ d.device_name }}</span>
            <el-tag :type="d.online_status === 'online' ? 'success' : 'info'" size="small">
              {{ d.online_status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </div>
          <div class="dc-area">{{ d.area_name || '-' }}</div>
          <ul class="dc-points">
            <li v-for="p in d.points" :key="p.point_id">
              <span class="p-name">{{ p.point_name }}</span>
              <span class="p-val">{{ p.value ?? '--' }}<em>{{ p.unit || '' }}</em></span>
            </li>
            <li v-if="!d.points.length" class="no-point">暂无测点</li>
          </ul>
        </div>
        <el-empty v-if="!devices.length && !loading" description="暂无设备" />
      </div>

      <div v-if="activeDevice" class="curve-panel">
        <div class="cp-head">
          <span class="cp-title">{{ activeDevice.device_name }} · 实时曲线</span>
          <el-select v-model="activePointId" size="small" style="width: 200px" @change="renderCurve">
            <el-option v-for="p in activeDevice.points" :key="p.point_id" :label="p.point_name" :value="p.point_id" />
          </el-select>
        </div>
        <div ref="curveRef" class="curve-box" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stat {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 12px;
  min-height: 80px;
}
.device-card {
  border: 1px solid #e5ecf8;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  background: #fff;
  transition: all 0.2s;
  &:hover {
    border-color: #9db8e8;
  }
  &.active {
    border-color: #2f7cf6;
    box-shadow: 0 0 0 2px rgba(47, 124, 246, 0.15);
  }
  .dc-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    .dc-name {
      font-weight: 600;
      color: #1f2d3d;
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  .dc-area {
    margin: 4px 0 8px;
    font-size: 12px;
    color: #8a94a6;
  }
  .dc-points {
    list-style: none;
    margin: 0;
    padding: 0;
    li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 3px 0;
      font-size: 12px;
      color: #40506b;
      .p-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 8px;
      }
      .p-val {
        font-weight: 600;
        color: #2f7cf6;
        em {
          font-style: normal;
          font-weight: 400;
          color: #8a94a6;
          margin-left: 2px;
          font-size: 11px;
        }
      }
      &.no-point {
        justify-content: center;
        color: #a6b1c2;
      }
    }
  }
}
.curve-panel {
  margin-top: 18px;
  border-top: 1px dashed #e5ecf8;
  padding-top: 14px;
  .cp-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    .cp-title {
      font-weight: 600;
      color: #1f2d3d;
    }
  }
  .curve-box {
    height: 280px;
  }
}
</style>
