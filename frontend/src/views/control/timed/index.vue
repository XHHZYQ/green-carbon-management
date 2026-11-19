<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { controlApi, type ControlDevice, type ControlPointItem, type TimedTaskItem } from '@/api/control'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const devices = ref<ControlDevice[]>([])
const table = useTable<TimedTaskItem>(controlApi.timedTasks, { keyword: '', device_id: undefined })

onMounted(async () => {
  table.load()
  devices.value = await controlApi.points()
})

const dialog = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})

const currentPoints = computed<ControlPointItem[]>(
  () => devices.value.find((d) => d.device_id === form.device_id)?.points || [],
)
const currentPoint = computed<ControlPointItem | undefined>(
  () => currentPoints.value.find((p) => p.point_key === form.point_key),
)

const CRON_PRESETS = [
  { label: '每天 08:00', value: '0 8 * * *' },
  { label: '每天 22:00', value: '0 22 * * *' },
  { label: '工作日 08:00', value: '0 8 * * 1-5' },
  { label: '工作日 18:30', value: '30 18 * * 1-5' },
  { label: '每小时', value: '0 * * * *' },
]

function onDeviceChange() {
  form.point_key = ''
  form.target_value = ''
}
function onPointChange() {
  const p = currentPoint.value
  if (!p) return
  form.target_value = p.point_type === 'enum' ? p.enum_options?.[0]?.value ?? '' : p.value_min ?? 0
}

function openCreate() {
  editingId.value = undefined
  Object.assign(form, {
    task_name: '',
    device_id: undefined,
    point_key: '',
    target_value: '',
    cron_expr: '0 8 * * *',
    repeat_desc: '每天 08:00',
    enable_status: 1,
  })
  dialog.value = true
}
function openEdit(row: TimedTaskItem) {
  editingId.value = row.id
  Object.assign(form, row)
  dialog.value = true
}
async function submit() {
  if (!form.task_name) return ElMessage.warning('请填写任务名称')
  if (!form.device_id || !form.point_key) return ElMessage.warning('请选择设备与控制点')
  if (!form.cron_expr) return ElMessage.warning('请填写 cron 表达式')
  form.target_value = String(form.target_value)
  if (editingId.value) await controlApi.updateTimedTask(editingId.value, { ...form })
  else await controlApi.createTimedTask({ ...form })
  ElMessage.success('保存成功')
  dialog.value = false
  table.load()
}
async function remove(row: TimedTaskItem) {
  await ElMessageBox.confirm(`确认删除定时任务「${row.task_name}」？`, '提示', { type: 'warning' })
  await controlApi.removeTimedTask(row.id)
  ElMessage.success('删除成功')
  table.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>定时控制任务</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="任务名称" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.device_id" placeholder="所属设备" clearable filterable style="width: 220px" @change="table.search()">
          <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-button type="primary" style="margin-left: auto" @click="openCreate">新增任务</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="task_name" label="任务名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="device_name" label="所属设备" min-width="160" show-overflow-tooltip />
        <el-table-column prop="point_key" label="控制点" width="130" />
        <el-table-column prop="target_value" label="目标值" width="90" />
        <el-table-column prop="cron_expr" label="Cron 表达式" width="130" />
        <el-table-column prop="repeat_desc" label="重复说明" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enable_status === 1 ? 'success' : 'info'" size="small">
              {{ row.enable_status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近执行" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_run_time) }}</template>
        </el-table-column>
        <el-table-column label="下次执行" width="170">
          <template #default="{ row }">{{ formatDateTime(row.next_run_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="dialog" :title="editingId ? '编辑定时任务' : '新增定时任务'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="任务名称" required><el-input v-model="form.task_name" /></el-form-item>
        <el-form-item label="所属设备" required>
          <el-select v-model="form.device_id" filterable style="width: 100%" @change="onDeviceChange">
            <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="控制点" required>
          <el-select v-model="form.point_key" style="width: 100%" @change="onPointChange">
            <el-option v-for="p in currentPoints" :key="p.point_key" :label="p.point_name" :value="p.point_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值" required>
          <el-select v-if="currentPoint?.point_type === 'enum'" v-model="form.target_value" style="width: 100%">
            <el-option v-for="opt in currentPoint?.enum_options || []" :key="String(opt.value)" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-input-number
            v-else
            v-model="form.target_value"
            :min="currentPoint?.value_min ?? undefined"
            :max="currentPoint?.value_max ?? undefined"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Cron 表达式" required>
          <el-input v-model="form.cron_expr" placeholder="分 时 日 月 周，如 0 8 * * 1-5" />
          <div class="cron-presets">
            <el-tag
              v-for="c in CRON_PRESETS"
              :key="c.value"
              size="small"
              effect="plain"
              class="preset"
              @click="form.cron_expr = c.value; form.repeat_desc = c.label"
            >
              {{ c.label }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="重复说明"><el-input v-model="form.repeat_desc" /></el-form-item>
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
.cron-presets {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  .preset {
    cursor: pointer;
  }
}
</style>
