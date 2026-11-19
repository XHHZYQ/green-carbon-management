<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { deviceApi, type DeviceItem } from '@/api/device'
import { monitorApi, type TopologyDetail, type TopologyItem, type TopologyNode } from '@/api/monitor'
import { pointApi, type PointItem } from '@/api/point'
import TopologyCanvas from './TopologyCanvas.vue'

const props = withDefaults(
  defineProps<{ topoType: 'topology' | 'plan'; variant?: 'grid' | 'floor'; title: string }>(),
  { variant: 'grid' },
)

const CANVAS_HEIGHT = 560
const list = ref<TopologyItem[]>([])
const currentId = ref<number>()
const current = ref<TopologyDetail>()
const nodes = ref<TopologyNode[]>([])
const editing = ref(false)
const devices = ref<DeviceItem[]>([])
const dialogPoints = ref<PointItem[]>([])
const canvasWrap = ref<HTMLDivElement>()
const autoRefresh = ref(false)
let timer: number | undefined

const listTitle = computed(() => `${props.title}列表`)
const dirtyNodes = computed(() => nodes.value.length)

const dialog = reactive({
  visible: false,
  isNew: true,
  form: {
    node_key: '',
    device_id: undefined as number | undefined,
    point_id: undefined as number | undefined,
    pos_x: 80,
    pos_y: 60,
    width: 160,
    height: 84,
    color: '#2f7cf6',
  },
})

onMounted(async () => {
  const d = await deviceApi.list({ page: 1, page_size: 200 })
  devices.value = d.items
  await loadList()
})

onBeforeUnmount(() => stopTimer())

async function loadList() {
  const res = await monitorApi.topologies({ topo_type: props.topoType, page: 1, page_size: 100 })
  list.value = res.items
  if (list.value.length && !list.value.some((t) => t.id === currentId.value)) {
    await selectTopo(list.value[0].id!)
  }
}

async function selectTopo(id: number) {
  if (editing.value && currentId.value !== id) {
    editing.value = false
  }
  currentId.value = id
  await reload()
  restartTimer()
}

async function reload() {
  if (!currentId.value) return
  current.value = await monitorApi.topology(currentId.value)
  nodes.value = current.value.nodes.map((n) => ({ ...n }))
}

async function createTopo() {
  const { value } = await ElMessageBox.prompt('请输入组态图名称', '新建', {
    inputPlaceholder: `如：${props.title}示例`,
    inputValidator: (v: string) => !!v?.trim() || '名称不能为空',
  }).catch(() => ({ value: '' }))
  if (!value) return
  const created = await monitorApi.createTopology({
    topo_code: `${props.topoType.toUpperCase()}_${Date.now()}`,
    topo_name: value.trim(),
    topo_type: props.topoType,
    status: 1,
    nodes: [],
  })
  ElMessage.success('新建成功')
  await loadList()
  if (created.id) await selectTopo(created.id)
}

async function removeTopo(item: TopologyItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${item.topo_name}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await monitorApi.removeTopology(item.id!)
  ElMessage.success('删除成功')
  if (currentId.value === item.id) {
    currentId.value = undefined
    current.value = undefined
    nodes.value = []
  }
  await loadList()
}

function startEdit() {
  stopTimer()
  editing.value = true
}
function cancelEdit() {
  editing.value = false
  reload()
}
async function saveEdit() {
  if (!currentId.value) return
  await monitorApi.updateTopology(currentId.value, {
    topo_name: current.value?.topo_name,
    topo_type: props.topoType,
    nodes: nodes.value.map(toPayload),
  })
  ElMessage.success('保存成功')
  editing.value = false
  await reload()
  restartTimer()
}

function toPayload(n: TopologyNode) {
  return {
    node_key: n.node_key,
    node_type: n.node_type || 'device',
    device_id: n.device_id ?? null,
    point_id: n.point_id ?? null,
    pos_x: Number(n.pos_x || 0),
    pos_y: Number(n.pos_y || 0),
    width: Number(n.width || 160),
    height: Number(n.height || 84),
    style_json: n.style_json || {},
    link_json: n.link_json || {},
  }
}

function onMove(node: TopologyNode, x: number, y: number) {
  const target = nodes.value.find((n) => n.node_key === node.node_key)
  if (target) {
    target.pos_x = x
    target.pos_y = y
  }
}

function openAdd() {
  Object.assign(dialog.form, {
    node_key: `n${Date.now()}`,
    device_id: undefined,
    point_id: undefined,
    pos_x: 80,
    pos_y: 60,
    width: 160,
    height: 84,
    color: '#2f7cf6',
  })
  dialogPoints.value = []
  dialog.isNew = true
  dialog.visible = true
}

async function openEdit(node: TopologyNode) {
  Object.assign(dialog.form, {
    node_key: node.node_key,
    device_id: node.device_id ?? undefined,
    point_id: node.point_id ?? undefined,
    pos_x: Number(node.pos_x || 0),
    pos_y: Number(node.pos_y || 0),
    width: Number(node.width || 160),
    height: Number(node.height || 84),
    color: (node.style_json as { color?: string } | null)?.color || '#2f7cf6',
  })
  dialog.isNew = false
  dialog.visible = true
  await loadDialogPoints()
}

async function loadDialogPoints() {
  if (!dialog.form.device_id) {
    dialogPoints.value = []
    return
  }
  const res = await pointApi.list({ device_id: dialog.form.device_id, page: 1, page_size: 200 })
  dialogPoints.value = res.items
}

function onDialogDeviceChange() {
  dialog.form.point_id = undefined
  loadDialogPoints()
}

function confirmNode() {
  if (!dialog.form.device_id) {
    ElMessage.warning('请选择设备')
    return
  }
  const device = devices.value.find((d) => d.id === dialog.form.device_id)
  const point = dialogPoints.value.find((p) => p.id === dialog.form.point_id)
  const data: TopologyNode = {
    node_key: dialog.form.node_key,
    node_type: 'device',
    device_id: dialog.form.device_id,
    point_id: dialog.form.point_id ?? null,
    pos_x: dialog.form.pos_x,
    pos_y: dialog.form.pos_y,
    width: dialog.form.width,
    height: dialog.form.height,
    style_json: { color: dialog.form.color },
    link_json: {},
    device_name: device?.device_name,
    point_name: point?.point_name,
    unit: point?.unit,
    value: null,
  }
  const idx = nodes.value.findIndex((n) => n.node_key === dialog.form.node_key)
  if (idx >= 0) nodes.value[idx] = { ...nodes.value[idx], ...data }
  else nodes.value.push(data)
  dialog.visible = false
}

function removeNode() {
  nodes.value = nodes.value.filter((n) => n.node_key !== dialog.form.node_key)
  dialog.visible = false
}

function restartTimer() {
  stopTimer()
  if (autoRefresh.value && !editing.value) {
    timer = window.setInterval(() => reload(), 3000)
  }
}
function stopTimer() {
  if (timer) window.clearInterval(timer)
  timer = undefined
}

watch(autoRefresh, () => restartTimer())

function exportPng() {
  const W = canvasWrap.value?.clientWidth || 960
  const H = CANVAS_HEIGHT
  const scale = 2
  const cv = document.createElement('canvas')
  cv.width = W * scale
  cv.height = H * scale
  const ctx = cv.getContext('2d')!
  ctx.scale(scale, scale)
  ctx.fillStyle = '#f7faff'
  ctx.fillRect(0, 0, W, H)
  ctx.strokeStyle = '#e6edfb'
  ctx.lineWidth = 1
  for (let x = 0; x < W; x += 20) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, H)
    ctx.stroke()
  }
  for (let y = 0; y < H; y += 20) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
    ctx.stroke()
  }
  const map = Object.fromEntries(nodes.value.map((n) => [n.node_key, n]))
  ctx.strokeStyle = '#9db8e8'
  ctx.lineWidth = 1.5
  for (const n of nodes.value) {
    const prevKey = (n.link_json as { prev?: string } | null)?.prev
    const prev = prevKey ? map[prevKey] : undefined
    if (!prev) continue
    ctx.beginPath()
    ctx.moveTo(Number(prev.pos_x || 0) + Number(prev.width || 160) / 2, Number(prev.pos_y || 0) + Number(prev.height || 84) / 2)
    ctx.lineTo(Number(n.pos_x || 0) + Number(n.width || 160) / 2, Number(n.pos_y || 0) + Number(n.height || 84) / 2)
    ctx.stroke()
  }
  for (const n of nodes.value) {
    const x = Number(n.pos_x || 0)
    const y = Number(n.pos_y || 0)
    const w = Number(n.width || 160)
    const h = Number(n.height || 84)
    const color = (n.style_json as { color?: string } | null)?.color || '#2f7cf6'
    ctx.fillStyle = '#fff'
    roundRect(ctx, x, y, w, h, 8)
    ctx.fill()
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.textAlign = 'center'
    ctx.fillStyle = '#1f2d3d'
    ctx.font = 'bold 13px sans-serif'
    ctx.fillText((n.device_name || n.node_key).slice(0, 12), x + w / 2, y + 24)
    ctx.fillStyle = color
    ctx.font = 'bold 18px sans-serif'
    ctx.fillText(n.value != null ? String(n.value) : '--', x + w / 2, y + 52)
    ctx.fillStyle = '#8a94a6'
    ctx.font = '11px sans-serif'
    ctx.fillText(`${n.point_name || ''} ${n.unit || ''}`.trim(), x + w / 2, y + 72)
  }
  cv.toBlob((blob) => {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${current.value?.topo_name || props.title}.png`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出 PNG')
  })
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
</script>

<template>
  <div class="topo-layout">
    <aside class="topo-side">
      <div class="side-head">
        <span>{{ listTitle }}</span>
        <el-button type="primary" size="small" @click="createTopo">新建</el-button>
      </div>
      <ul class="topo-list">
        <li
          v-for="t in list"
          :key="t.id"
          :class="{ active: t.id === currentId }"
          @click="selectTopo(t.id!)"
        >
          <div class="t-name">{{ t.topo_name }}</div>
          <el-icon class="t-del" @click.stop="removeTopo(t)"><Delete /></el-icon>
        </li>
        <li v-if="!list.length" class="empty">暂无数据</li>
      </ul>
    </aside>

    <section class="topo-main">
      <div v-if="!current" class="topo-placeholder">请选择左侧{{ title }}</div>
      <template v-else>
        <div class="topo-toolbar">
          <div class="topo-name">{{ current.topo_name }}</div>
          <div class="tool-actions">
            <el-switch v-model="autoRefresh" :disabled="editing" active-text="自动刷新" inline-prompt />
            <el-button v-if="!editing" @click="reload">刷新</el-button>
            <el-button @click="exportPng">导出PNG</el-button>
            <el-button v-if="!editing" type="primary" @click="startEdit">编辑</el-button>
            <template v-else>
              <el-button type="success" @click="openAdd">新增节点</el-button>
              <el-button @click="cancelEdit">取消</el-button>
              <el-button type="primary" @click="saveEdit">保存</el-button>
            </template>
          </div>
        </div>

        <el-alert
          v-if="editing"
          type="info"
          :closable="false"
          show-icon
          :title="`编辑模式：拖动节点调整位置，双击节点修改，共 ${dirtyNodes} 个节点`"
          class="edit-tip"
        />

        <div ref="canvasWrap">
          <TopologyCanvas
            :nodes="nodes"
            :editable="editing"
            :variant="variant"
            :height="CANVAS_HEIGHT"
            @move="onMove"
            @dblclick="openEdit"
          />
        </div>
      </template>
    </section>

    <el-dialog v-model="dialog.visible" :title="dialog.isNew ? '新增节点' : '编辑节点'" width="460px">
      <el-form label-width="72px">
        <el-form-item label="设备">
          <el-select v-model="dialog.form.device_id" placeholder="选择设备" filterable style="width: 100%" @change="onDialogDeviceChange">
            <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="测点">
          <el-select v-model="dialog.form.point_id" placeholder="选择测点" clearable filterable style="width: 100%">
            <el-option v-for="p in dialogPoints" :key="p.id" :label="p.point_name" :value="p.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="X / Y">
          <el-input-number v-model="dialog.form.pos_x" :min="0" :max="1400" controls-position="right" />
          <el-input-number v-model="dialog.form.pos_y" :min="0" :max="800" controls-position="right" />
        </el-form-item>
        <el-form-item label="宽 / 高">
          <el-input-number v-model="dialog.form.width" :min="80" :max="420" controls-position="right" />
          <el-input-number v-model="dialog.form.height" :min="48" :max="240" controls-position="right" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="dialog.form.color" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="!dialog.isNew" type="danger" plain @click="removeNode">删除节点</el-button>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmNode">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.topo-layout {
  display: flex;
  gap: 16px;
}
.topo-side {
  width: 220px;
  flex-shrink: 0;
  border: 1px solid #e5ecf8;
  border-radius: 8px;
  overflow: hidden;
  .side-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    font-weight: 600;
    color: #1f2d3d;
    background: #f2f7ff;
    border-bottom: 1px solid #e5ecf8;
  }
}
.topo-list {
  list-style: none;
  margin: 0;
  padding: 4px;
  max-height: 620px;
  overflow: auto;
  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    color: #40506b;
    font-size: 13px;
    &:hover {
      background: #f2f7ff;
    }
    &.active {
      background: #e6f0ff;
      color: #2f7cf6;
      font-weight: 600;
    }
    &.empty {
      justify-content: center;
      color: #a6b1c2;
      cursor: default;
    }
    .t-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .t-del {
      color: #f56c6c;
      opacity: 0.6;
      &:hover {
        opacity: 1;
      }
    }
  }
}
.topo-main {
  flex: 1;
  min-width: 0;
}
.topo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  .topo-name {
    font-size: 16px;
    font-weight: 600;
    color: #1f2d3d;
  }
  .tool-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
.edit-tip {
  margin-bottom: 12px;
}
.topo-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #a6b1c2;
}
</style>
