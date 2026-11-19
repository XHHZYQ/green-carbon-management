<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { deviceApi, type DeviceItem } from '@/api/device'
import { collectTaskApi, type CollectTaskItem } from '@/api/point'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const devices = ref<DeviceItem[]>([])
const table = useTable<CollectTaskItem>(collectTaskApi.list, { keyword: '', device_id: undefined })

onMounted(async () => {
  table.load()
  const d = await deviceApi.list({ page: 1, page_size: 200 })
  devices.value = d.items
})

const dialog = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})

function openCreate() {
  editingId.value = undefined
  Object.assign(form, { device_id: undefined, task_name: '', collect_mode: 'period', period_sec: 60, range_desc: '全天', enable_status: 1 })
  dialog.value = true
}
function openEdit(row: CollectTaskItem) {
  editingId.value = row.id
  Object.assign(form, row)
  dialog.value = true
}
async function submit() {
  if (!form.device_id || !form.task_name) return ElMessage.warning('请选择设备并填写任务名称')
  if (editingId.value) await collectTaskApi.update(editingId.value, { ...form })
  else await collectTaskApi.create({ ...form })
  ElMessage.success('保存成功')
  dialog.value = false
  table.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>采集任务</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="任务名称" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.device_id" placeholder="所属设备" clearable filterable style="width: 220px" @change="table.search()">
          <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-button type="primary" style="margin-left: auto" @click="openCreate">新增任务</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="device_name" label="所属设备" min-width="170" show-overflow-tooltip />
        <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="采集方式" width="120">
          <template #default="{ row }">{{ row.collect_mode === 'period' ? '周期采集' : row.collect_mode === 'change' ? '变化采集' : row.collect_mode }}</template>
        </el-table-column>
        <el-table-column prop="period_sec" label="周期(秒)" width="100" />
        <el-table-column prop="range_desc" label="采集范围" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enable_status === 1 ? 'success' : 'info'" size="small">{{ row.enable_status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近执行" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_run_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="dialog" :title="editingId ? '编辑采集任务' : '新增采集任务'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="所属设备" required>
          <el-select v-model="form.device_id" filterable style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称" required><el-input v-model="form.task_name" /></el-form-item>
        <el-form-item label="采集方式">
          <el-select v-model="form.collect_mode" style="width: 100%">
            <el-option label="周期采集" value="period" />
            <el-option label="变化采集" value="change" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期(秒)"><el-input-number v-model="form.period_sec" :min="1" /></el-form-item>
        <el-form-item label="采集范围"><el-input v-model="form.range_desc" /></el-form-item>
        <el-form-item label="启用状态"><el-switch v-model="form.enable_status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
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
</style>
