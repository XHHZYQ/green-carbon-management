<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { areaApi, deviceApi, type AreaNode, type DeviceItem } from '@/api/device'
import { deviceTypeApi, protocolApi, type DeviceType, type Protocol } from '@/api/config'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const table = useTable<DeviceItem>(deviceApi.list, {
  keyword: '',
  area_id: undefined,
  device_type_id: undefined,
  online_status: undefined,
  status: undefined,
})

const areaTree = ref<AreaNode[]>([])
const types = ref<DeviceType[]>([])
const protocols = ref<Protocol[]>([])
const treeProps = { label: 'area_name', value: 'id', children: 'children' }

const dialogVisible = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})

async function init() {
  const [a, t, p] = await Promise.all([areaApi.tree(), deviceTypeApi.list({ page: 1, page_size: 100 }), protocolApi.list({ page: 1, page_size: 100 })])
  areaTree.value = a
  types.value = t.items
  protocols.value = p.items
  table.load()
}
onMounted(init)

function openDetail(row: DeviceItem) {
  router.push({ path: '/device/detail', query: { id: row.id } })
}

async function openEdit(row: DeviceItem) {
  const detail = await deviceApi.detail(row.id as number)
  editingId.value = row.id
  Object.assign(form, {
    device_name: detail.device_name,
    device_type_id: detail.device_type_id,
    area_id: detail.area_id,
    protocol_id: detail.protocol_id,
    install_location: detail.install_location,
    remark: detail.remark,
    params: detail.params.map((c) => ({ param_key: c.param_key, param_value: c.param_value })),
  })
  dialogVisible.value = true
}

async function submit() {
  if (!form.device_name) return ElMessage.warning('请输入设备名称')
  const params: Record<string, string> = {}
  for (const c of form.params || []) {
    if (c.param_key) params[c.param_key] = c.param_value
  }
  await deviceApi.update(editingId.value as number, { ...form, params })
  ElMessage.success('保存成功')
  dialogVisible.value = false
  table.load()
}

async function toggleOnline(row: DeviceItem) {
  const online = row.online_status !== 'online'
  await deviceApi.setOnline(row.id as number, online)
  ElMessage.success(online ? '设备已上线' : '设备已下线')
  table.load()
}

async function remove(row: DeviceItem) {
  await ElMessageBox.confirm(`确定删除设备「${row.device_name}」？将同时删除其测点、采集任务与历史数据。`, '提示', { type: 'warning' })
  await deviceApi.remove(row.id as number)
  ElMessage.success('删除成功')
  table.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备台账</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="设备编号 / 名称" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-tree-select v-model="table.query.area_id" :data="areaTree" :props="treeProps" check-strictly clearable placeholder="所属区域" style="width: 180px" @change="table.search()" />
        <el-select v-model="table.query.device_type_id" placeholder="设备类型" clearable style="width: 160px" @change="table.search()">
          <el-option v-for="t in types" :key="t.id" :label="t.type_name" :value="t.id" />
        </el-select>
        <el-select v-model="table.query.online_status" placeholder="在线状态" clearable style="width: 130px" @change="table.search()">
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <el-button type="primary" @click="router.push('/access/wizard')">新增设备</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="device_code" label="设备编号" width="170" />
        <el-table-column prop="device_name" label="设备名称" min-width="170" show-overflow-tooltip />
        <el-table-column prop="type_name" label="设备类型" width="150" />
        <el-table-column prop="area_name" label="所属区域" width="130" />
        <el-table-column prop="protocol_name" label="通信协议" width="130" />
        <el-table-column prop="install_location" label="安装位置" min-width="130" show-overflow-tooltip />
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
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="toggleOnline(row)">{{ row.online_status === 'online' ? '下线' : '上线' }}</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
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

    <el-dialog v-model="dialogVisible" title="编辑设备" width="640px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备名称"><el-input v-model="form.device_name" /></el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="form.device_type_id" style="width: 100%">
            <el-option v-for="t in types" :key="t.id" :label="t.type_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属区域">
          <el-tree-select v-model="form.area_id" :data="areaTree" :props="treeProps" check-strictly style="width: 100%" />
        </el-form-item>
        <el-form-item label="通信协议">
          <el-select v-model="form.protocol_id" style="width: 100%">
            <el-option v-for="p in protocols" :key="p.id" :label="p.protocol_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="安装位置"><el-input v-model="form.install_location" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="连接参数">
          <div style="width: 100%">
            <div v-for="(c, i) in form.params" :key="i" class="param-row">
              <el-input v-model="c.param_key" placeholder="参数名" style="width: 40%" />
              <el-input v-model="c.param_value" placeholder="参数值" style="width: 50%" />
              <el-button link type="danger" @click="form.params.splice(i, 1)">删除</el-button>
            </div>
            <el-button link type="primary" @click="form.params.push({ param_key: '', param_value: '' })">+ 添加参数</el-button>
          </div>
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
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
.param-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
