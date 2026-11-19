<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { controlApi, type ControlDevice, type ControlPointItem } from '@/api/control'

const loading = ref(false)
const devices = ref<ControlDevice[]>([])
const keyword = ref('')
const selectedIds = ref<number[]>([])
const values = reactive<Record<string, any>>({})

const onlineMap: Record<string, { text: string; type: 'success' | 'info' | 'warning' | 'danger' }> = {
  online: { text: '在线', type: 'success' },
  offline: { text: '离线', type: 'info' },
  abnormal: { text: '异常', type: 'danger' },
}

function vkey(deviceId: number, pointKey: string) {
  return `${deviceId}:${pointKey}`
}

function initValue(p: ControlPointItem) {
  if (p.point_type === 'enum') return p.enum_options?.[0]?.value ?? ''
  if (p.point_type === 'number') return p.value_min ?? 0
  return p.current_value ?? ''
}

async function load() {
  loading.value = true
  try {
    devices.value = await controlApi.points({ keyword: keyword.value || undefined })
    selectedIds.value = []
    devices.value.forEach((d) =>
      d.points.forEach((p) => {
        values[vkey(d.device_id, p.point_key)] = initValue(p)
      }),
    )
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function send(device: ControlDevice, p: ControlPointItem) {
  const value = values[vkey(device.device_id, p.point_key)]
  if (value === '' || value === undefined || value === null) return ElMessage.warning('请先设定目标值')
  if (p.dangerous) {
    await ElMessageBox.confirm(
      `「${device.device_name} - ${p.point_name}」为危险控制点，确认下发？`,
      '危险操作确认',
      { type: 'warning' },
    )
  }
  await controlApi.send({
    device_id: device.device_id,
    point_key: p.point_key,
    target_value: String(value),
    need_confirm: p.dangerous,
  })
  ElMessage.success('指令已下发')
}

/* ---------------- 批量下发 ---------------- */
const batchDialog = ref(false)
const batchForm = reactive<{ point_key: string; target_value: any }>({ point_key: '', target_value: '' })

const selectedDevices = computed(() => devices.value.filter((d) => selectedIds.value.includes(d.device_id)))

const batchPoints = computed(() => {
  const map = new Map<string, ControlPointItem>()
  selectedDevices.value.forEach((d) => d.points.forEach((p) => !map.has(p.point_key) && map.set(p.point_key, p)))
  return [...map.values()]
})
const currentBatchPoint = computed(() => batchPoints.value.find((p) => p.point_key === batchForm.point_key))

function onBatchPointChange() {
  const p = currentBatchPoint.value
  batchForm.target_value = p ? initValue(p) : ''
}

function openBatch() {
  if (!selectedDevices.value.length) return ElMessage.warning('请先勾选设备')
  batchForm.point_key = ''
  batchForm.target_value = ''
  batchDialog.value = true
}

async function submitBatch() {
  if (!batchForm.point_key) return ElMessage.warning('请选择控制点')
  const items = selectedDevices.value
    .filter((d) => d.points.some((p) => p.point_key === batchForm.point_key))
    .map((d) => ({ device_id: d.device_id, point_key: batchForm.point_key, target_value: String(batchForm.target_value) }))
  if (!items.length) return ElMessage.warning('所选设备均不含该控制点')
  await ElMessageBox.confirm(`将对 ${items.length} 台设备下发控制指令，确认执行？`, '批量下发确认', { type: 'warning' })
  const res = await controlApi.batch({ items })
  ElMessage.success(`已下发 ${res.count} 条指令`)
  batchDialog.value = false
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备控制面板</h2></div>

      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="设备名称" clearable style="width: 200px" @keyup.enter="load" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="keyword = ''; load()">重置</el-button>
        <span class="batch-hint">已选 {{ selectedIds.length }} 台设备</span>
        <el-button type="warning" style="margin-left: auto" :disabled="!selectedIds.length" @click="openBatch">
          批量下发
        </el-button>
      </div>

      <div v-loading="loading" class="device-grid">
        <el-empty v-if="!devices.length && !loading" description="暂无可控设备" />
        <el-row :gutter="14">
          <el-col v-for="d in devices" :key="d.device_id" :xs="24" :sm="12" :lg="8" :xl="6">
            <el-card class="ctrl-card" shadow="hover">
              <template #header>
                <div class="ctrl-head">
                  <el-checkbox v-model="selectedIds" :value="d.device_id" />
                  <div class="ctrl-title">
                    <div class="name">{{ d.device_name }}</div>
                    <div class="sub">{{ d.device_code }} · {{ d.area_name || '未分区' }}</div>
                  </div>
                  <el-tag :type="onlineMap[d.online_status]?.type || 'info'" size="small" effect="light">
                    {{ onlineMap[d.online_status]?.text || d.online_status }}
                  </el-tag>
                </div>
              </template>

              <div v-for="p in d.points" :key="p.point_key" class="point-row">
                <div class="point-label">
                  <span>{{ p.point_name }}</span>
                  <el-tag v-if="p.dangerous" type="danger" size="small" effect="plain">危险</el-tag>
                </div>
                <div class="point-op">
                  <el-select
                    v-if="p.point_type === 'enum'"
                    v-model="values[vkey(d.device_id, p.point_key)]"
                    size="small"
                    style="width: 96px"
                  >
                    <el-option
                      v-for="opt in p.enum_options || []"
                      :key="String(opt.value)"
                      :label="opt.label"
                      :value="opt.value"
                    />
                  </el-select>
                  <el-input-number
                    v-else
                    v-model="values[vkey(d.device_id, p.point_key)]"
                    :min="p.value_min ?? undefined"
                    :max="p.value_max ?? undefined"
                    size="small"
                    controls-position="right"
                    style="width: 120px"
                  />
                  <el-button type="primary" size="small" @click="send(d, p)">下发</el-button>
                </div>
                <div v-if="p.current_value !== null && p.current_value !== undefined" class="point-cur">
                  当前：{{ p.current_value }}
                </div>
              </div>

              <el-empty v-if="!d.points.length" description="无控制点" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>

    <el-dialog v-model="batchDialog" title="批量下发" width="480px">
      <el-form :model="batchForm" label-width="90px">
        <el-form-item label="控制点" required>
          <el-select v-model="batchForm.point_key" style="width: 100%" @change="onBatchPointChange">
            <el-option v-for="p in batchPoints" :key="p.point_key" :label="p.point_name" :value="p.point_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值" required>
          <el-select v-if="currentBatchPoint?.point_type === 'enum'" v-model="batchForm.target_value" style="width: 100%">
            <el-option
              v-for="opt in currentBatchPoint?.enum_options || []"
              :key="String(opt.value)"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-input-number
            v-else
            v-model="batchForm.target_value"
            :min="currentBatchPoint?.value_min ?? undefined"
            :max="currentBatchPoint?.value_max ?? undefined"
            style="width: 100%"
          />
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon title="批量下发将作用于所选设备中具备该控制点的全部设备" />
      </el-form>
      <template #footer>
        <el-button @click="batchDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">确认下发</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.batch-hint {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.device-grid {
  min-height: 120px;
  :deep(.el-col) {
    margin-bottom: 14px;
  }
}
.ctrl-card {
  height: 100%;
  .ctrl-head {
    display: flex;
    align-items: center;
    gap: 10px;
    .ctrl-title {
      flex: 1;
      min-width: 0;
      .name {
        font-weight: 600;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .sub {
        color: var(--el-text-color-secondary);
        font-size: 12px;
      }
    }
  }
}
.point-row {
  padding: 6px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  &:last-child {
    border-bottom: none;
  }
  .point-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    margin-bottom: 6px;
  }
  .point-op {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .point-cur {
    margin-top: 4px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
