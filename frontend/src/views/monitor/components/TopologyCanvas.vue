<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TopologyNode } from '@/api/monitor'

const props = withDefaults(
  defineProps<{
    nodes: TopologyNode[]
    editable?: boolean
    variant?: 'grid' | 'floor'
    height?: number
  }>(),
  { editable: false, variant: 'grid', height: 560 },
)

const emit = defineEmits<{
  (e: 'move', node: TopologyNode, x: number, y: number): void
  (e: 'dblclick', node: TopologyNode): void
  (e: 'select', node: TopologyNode): void
}>()

const selectedKey = ref<string>()
const num = (v: unknown) => Number(v || 0)

const nodeMap = computed(() => Object.fromEntries(props.nodes.map((n) => [n.node_key, n])))
const links = computed(() => {
  const list: { x1: number; y1: number; x2: number; y2: number }[] = []
  for (const n of props.nodes) {
    const prevKey = (n.link_json as { prev?: string } | null)?.prev
    const prev = prevKey ? nodeMap.value[prevKey] : undefined
    if (!prev) continue
    list.push({
      x1: num(prev.pos_x) + num(prev.width) / 2,
      y1: num(prev.pos_y) + num(prev.height) / 2,
      x2: num(n.pos_x) + num(n.width) / 2,
      y2: num(n.pos_y) + num(n.height) / 2,
    })
  }
  return list
})

function nodeStyle(n: TopologyNode) {
  const color = (n.style_json as { color?: string } | null)?.color || '#2f7cf6'
  return {
    left: `${num(n.pos_x)}px`,
    top: `${num(n.pos_y)}px`,
    width: `${num(n.width) || 160}px`,
    height: `${num(n.height) || 84}px`,
    borderColor: color,
  }
}

let drag: { node: TopologyNode; startX: number; startY: number; origX: number; origY: number } | null = null

function onDown(e: MouseEvent, node: TopologyNode) {
  selectedKey.value = node.node_key
  emit('select', node)
  if (!props.editable) return
  drag = { node, startX: e.clientX, startY: e.clientY, origX: num(node.pos_x), origY: num(node.pos_y) }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(e: MouseEvent) {
  if (!drag) return
  emit(
    'move',
    drag.node,
    Math.max(0, Math.round(drag.origX + e.clientX - drag.startX)),
    Math.max(0, Math.round(drag.origY + e.clientY - drag.startY)),
  )
}

function onUp() {
  drag = null
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
}
</script>

<template>
  <div class="topo-canvas" :class="[variant, { 'is-editable': editable }]" :style="{ height: `${height}px` }">
    <svg class="topo-links" :width="'100%'" :height="height">
      <line v-for="(l, i) in links" :key="i" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" />
    </svg>

    <div
      v-for="n in nodes"
      :key="n.node_key"
      class="topo-node"
      :class="{ active: selectedKey === n.node_key }"
      :style="nodeStyle(n)"
      @mousedown="onDown($event, n)"
      @dblclick="emit('dblclick', n)"
    >
      <div class="node-title">{{ n.device_name || n.node_key }}</div>
      <div class="node-value">{{ n.value ?? '--' }}<span class="unit">{{ n.unit || '' }}</span></div>
      <div class="node-point">{{ n.point_name || '' }}</div>
    </div>

    <div v-if="!nodes.length" class="topo-empty">暂无节点，点击「编辑」后新增</div>
  </div>
</template>

<style scoped lang="scss">
.topo-canvas {
  position: relative;
  width: 100%;
  overflow: hidden;
  border: 1px solid #dfe8f7;
  border-radius: 8px;
  background-color: #f7faff;
  background-size: 20px 20px;
  background-image: linear-gradient(#e8eefb 1px, transparent 1px), linear-gradient(90deg, #e8eefb 1px, transparent 1px);

  &.floor {
    background-size: 40px 40px;
    background-image: linear-gradient(rgba(47, 124, 246, 0.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(47, 124, 246, 0.08) 1px, transparent 1px),
      radial-gradient(circle at 30% 35%, rgba(47, 124, 246, 0.06), transparent 45%),
      radial-gradient(circle at 72% 68%, rgba(47, 200, 160, 0.08), transparent 40%);
  }
}
.topo-links {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  line {
    stroke: #9db8e8;
    stroke-width: 1.5;
    stroke-dasharray: 4 3;
  }
}
.topo-node {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 6px 10px;
  border: 2px solid #2f7cf6;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(47, 124, 246, 0.12);
  cursor: default;
  user-select: none;

  &.active {
    box-shadow: 0 0 0 2px rgba(47, 124, 246, 0.35);
  }
  .node-title {
    font-size: 12px;
    color: #1f2d3d;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .node-value {
    font-size: 20px;
    font-weight: 700;
    color: #2f7cf6;
    line-height: 1.1;
    .unit {
      margin-left: 2px;
      font-size: 11px;
      font-weight: 400;
      color: #8a94a6;
    }
  }
  .node-point {
    font-size: 11px;
    color: #8a94a6;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
.is-editable .topo-node {
  cursor: move;
}
.topo-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #a6b1c2;
  font-size: 13px;
}
</style>
