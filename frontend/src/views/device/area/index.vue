<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { areaApi, deviceApi, type AreaNode, type DeviceItem } from '@/api/device'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const areaTree = ref<AreaNode[]>([])
const treeProps = { label: 'area_name', value: 'id', children: 'children' }
const currentArea = ref<AreaNode | null>(null)
const table = useTable<DeviceItem>(deviceApi.list, { area_id: undefined })

const dialogVisible = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})
const areaTypes = ['园区', '楼栋', '区域', '房间', '站点']

async function loadAreas() {
  areaTree.value = await areaApi.tree()
}
onMounted(async () => {
  await loadAreas()
  table.load()
})

function onAreaClick(node: AreaNode) {
  currentArea.value = node
  table.query.area_id = node.id
  table.search()
}

function resetArea() {
  currentArea.value = null
  table.query.area_id = undefined
  table.search()
}

function openCreate() {
  editingId.value = undefined
  Object.assign(form, { area_code: '', area_name: '', area_type: '区域', parent_id: currentArea.value?.id ?? null, sort_no: 0, status: 1 })
  dialogVisible.value = true
}

function openEdit(node: AreaNode) {
  editingId.value = node.id
  Object.assign(form, {
    area_code: node.area_code,
    area_name: node.area_name,
    area_type: node.area_type,
    parent_id: node.parent_id,
    sort_no: node.sort_no,
    status: node.status,
  })
  dialogVisible.value = true
}

async function submit() {
  if (!form.area_code || !form.area_name) return ElMessage.warning('请填写区域编码与名称')
  if (editingId.value) await areaApi.update(editingId.value, { ...form })
  else await areaApi.create({ ...form })
  ElMessage.success('保存成功')
  dialogVisible.value = false
  await loadAreas()
}

async function removeArea(node: AreaNode) {
  await ElMessageBox.confirm(`确定删除区域「${node.area_name}」？`, '提示', { type: 'warning' })
  await areaApi.remove(node.id)
  ElMessage.success('删除成功')
  if (currentArea.value?.id === node.id) resetArea()
  await loadAreas()
}
</script>

<template>
  <div class="page-container">
    <div class="area-layout">
      <div class="page-card area-tree-card">
        <div class="page-title">
          <h2>区域分组</h2>
          <el-button type="primary" size="small" @click="openCreate">新增区域</el-button>
        </div>
        <el-tree
          :data="areaTree"
          :props="treeProps"
          node-key="id"
          default-expand-all
          highlight-current
          :expand-on-click-node="false"
          @node-click="onAreaClick"
        >
          <template #default="{ data }">
            <div class="area-node">
              <span>{{ data.area_name }}</span>
              <span class="area-actions">
                <el-button link type="primary" size="small" @click.stop="openEdit(data)">编辑</el-button>
                <el-button link type="danger" size="small" @click.stop="removeArea(data)">删除</el-button>
              </span>
            </div>
          </template>
        </el-tree>
      </div>

      <div class="page-card area-table-card">
        <div class="page-title">
          <h2>{{ currentArea ? `${currentArea.area_name} · 设备` : '全部设备' }}</h2>
          <el-button size="small" @click="resetArea">查看全部</el-button>
        </div>
        <el-table v-loading="table.loading" :data="table.list" border height="520">
          <el-table-column prop="device_code" label="设备编号" width="170" />
          <el-table-column prop="device_name" label="设备名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="type_name" label="设备类型" width="140" />
          <el-table-column label="在线状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.online_status === 'online' ? 'success' : 'info'" size="small">
                {{ row.online_status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最近在线" width="170">
            <template #default="{ row }">{{ formatDateTime(row.last_online_time) }}</template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="table-pagination"
          :current-page="table.query.page"
          :page-size="table.query.page_size"
          :total="table.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="table.changePage"
          @size-change="table.changeSize"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑区域' : '新增区域'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="区域编码"><el-input v-model="form.area_code" :disabled="!!editingId" /></el-form-item>
        <el-form-item label="区域名称"><el-input v-model="form.area_name" /></el-form-item>
        <el-form-item label="区域类型">
          <el-select v-model="form.area_type" style="width: 100%">
            <el-option v-for="t in areaTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级区域">
          <el-tree-select v-model="form.parent_id" :data="areaTree" :props="treeProps" check-strictly clearable style="width: 100%" />
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_no" :min="0" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.area-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.area-tree-card {
  width: 320px;
  flex-shrink: 0;
}
.area-table-card {
  flex: 1;
  min-width: 0;
}
.area-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 6px;
}
.area-actions {
  display: none;
}
.area-node:hover .area-actions {
  display: inline-flex;
}
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
