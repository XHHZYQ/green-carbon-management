<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sceneApi, type SceneActionItem, type SceneItem } from '@/api/scene'
import { controlApi, type ControlDevice, type ControlPointItem } from '@/api/control'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const ICONS = ['Sunrise', 'Moon', 'Present', 'Coffee', 'TrendCharts', 'Lock', 'MagicStick']

const devices = ref<ControlDevice[]>([])
const table = useTable<SceneItem>(sceneApi.list, { keyword: '', enable_status: undefined })

onMounted(async () => {
  table.load()
  devices.value = await controlApi.points()
})

// ---------------- 场景 新增/编辑 ----------------
const dialog = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})

function openCreate() {
  editingId.value = undefined
  Object.assign(form, { scene_code: '', scene_name: '', icon: 'MagicStick', description: '', enable_status: 1 })
  dialog.value = true
}
function openEdit(row: SceneItem) {
  editingId.value = row.id
  Object.assign(form, row)
  dialog.value = true
}
async function submit() {
  if (!form.scene_code || !form.scene_name) return ElMessage.warning('请填写场景编码与名称')
  if (editingId.value) await sceneApi.update(editingId.value, { ...form })
  else await sceneApi.create({ ...form })
  ElMessage.success('保存成功')
  dialog.value = false
  table.load()
}
async function remove(row: SceneItem) {
  await ElMessageBox.confirm(`确认删除场景「${row.scene_name}」？`, '提示', { type: 'warning' })
  await sceneApi.remove(row.id)
  ElMessage.success('删除成功')
  table.load()
}
async function toggleEnable(row: SceneItem) {
  await sceneApi.setEnable(row.id, row.enable_status)
  ElMessage.success('操作成功')
}
async function execScene(row: SceneItem) {
  const r = await sceneApi.exec(row.id)
  ElMessage.success(`执行完成：成功 ${r.success_count} / 共 ${r.total_count}`)
  table.load()
}

// ---------------- 场景动作 ----------------
const actionDialog = ref(false)
const currentScene = ref<SceneItem>()
const actionList = ref<SceneActionItem[]>([])
const actionForm = reactive<Record<string, any>>({})
const actionEditingId = ref<number>()

const actionPoints = computed<ControlPointItem[]>(
  () => devices.value.find((d) => d.device_id === actionForm.device_id)?.points || [],
)
const actionPoint = computed<ControlPointItem | undefined>(
  () => actionPoints.value.find((p) => p.point_key === actionForm.point_key),
)

async function openActions(row: SceneItem) {
  currentScene.value = row
  actionDialog.value = true
  actionList.value = await sceneApi.actions(row.id)
}
async function refreshActions() {
  if (currentScene.value) actionList.value = await sceneApi.actions(currentScene.value.id)
}
function resetActionForm() {
  actionEditingId.value = undefined
  Object.assign(actionForm, { device_id: undefined, point_key: '', target_value: '', delay_sec: 0, sort_no: 0 })
}
function openActionCreate() {
  resetActionForm()
}
function openActionEdit(a: SceneActionItem) {
  actionEditingId.value = a.id
  Object.assign(actionForm, { ...a })
}
function onActionDevice() {
  actionForm.point_key = ''
  actionForm.target_value = ''
}
function onActionPoint() {
  const p = actionPoint.value
  if (!p) return
  actionForm.target_value = p.point_type === 'enum' ? p.enum_options?.[0]?.value ?? '' : p.value_min ?? 0
}
async function submitAction() {
  if (!currentScene.value) return
  if (!actionForm.device_id || !actionForm.point_key) return ElMessage.warning('请选择设备与控制点')
  actionForm.target_value = String(actionForm.target_value)
  if (actionEditingId.value) await sceneApi.updateAction(actionEditingId.value, { ...actionForm })
  else await sceneApi.createAction(currentScene.value.id, { ...actionForm })
  ElMessage.success('保存成功')
  resetActionForm()
  await refreshActions()
  table.load()
}
async function removeAction(a: SceneActionItem) {
  await ElMessageBox.confirm('确认删除该动作？', '提示', { type: 'warning' })
  await sceneApi.removeAction(a.id)
  ElMessage.success('删除成功')
  await refreshActions()
  table.load()
}

// ---------------- 场景定时 ----------------
const scheduleDialog = ref(false)
const scheduleForm = reactive<Record<string, any>>({})
const CRON_PRESETS = [
  { label: '上班 08:00', value: '0 8 * * 1-5' },
  { label: '下班 18:30', value: '30 18 * * 1-5' },
  { label: '午间 12:00', value: '0 12 * * 1-5' },
  { label: '每天 07:00', value: '0 7 * * *' },
]
function openSchedule(row: SceneItem) {
  currentScene.value = row
  Object.assign(scheduleForm, {
    cron_expr: row.cron_expr || '0 8 * * 1-5',
    repeat_desc: row.repeat_desc || '工作日 08:00',
    enable_status: row.schedule_enable ?? 0,
  })
  scheduleDialog.value = true
}
async function submitSchedule() {
  if (!currentScene.value) return
  if (!scheduleForm.cron_expr) return ElMessage.warning('请填写 cron 表达式')
  await sceneApi.saveSchedule(currentScene.value.id, { ...scheduleForm })
  ElMessage.success('保存成功')
  scheduleDialog.value = false
  table.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>场景管理</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="场景名称" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.enable_status" placeholder="状态" clearable style="width: 120px" @change="table.search()">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-button type="primary" style="margin-left: auto" @click="openCreate">新增场景</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="scene_name" label="场景名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="scene_code" label="场景编码" width="150" />
        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
        <el-table-column prop="action_count" label="动作数" width="80" />
        <el-table-column label="定时" width="140">
          <template #default="{ row }">
            <span v-if="row.cron_expr">{{ row.cron_expr }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.enable_status" :active-value="1" :inactive-value="0" @change="toggleEnable(row)" />
          </template>
        </el-table-column>
        <el-table-column label="最近执行" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_exec_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="execScene(row)">执行</el-button>
            <el-button link type="primary" @click="openActions(row)">动作</el-button>
            <el-button link type="primary" @click="openSchedule(row)">定时</el-button>
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

    <!-- 场景 新增/编辑 -->
    <el-dialog v-model="dialog" :title="editingId ? '编辑场景' : '新增场景'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="场景编码" required><el-input v-model="form.scene_code" placeholder="如 SCENE_WORK" /></el-form-item>
        <el-form-item label="场景名称" required><el-input v-model="form.scene_name" /></el-form-item>
        <el-form-item label="图标">
          <el-select v-model="form.icon" style="width: 100%">
            <el-option v-for="i in ICONS" :key="i" :label="i" :value="i" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="启用状态"><el-switch v-model="form.enable_status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 场景动作 -->
    <el-dialog v-model="actionDialog" :title="`场景动作 - ${currentScene?.scene_name || ''}`" width="720px">
      <el-table :data="actionList" border size="small">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="device_name" label="设备" min-width="130" show-overflow-tooltip />
        <el-table-column prop="point_key" label="控制点" width="120" />
        <el-table-column prop="target_value" label="目标值" width="90" />
        <el-table-column prop="delay_sec" label="延迟(秒)" width="90" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="openActionEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="removeAction(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">{{ actionEditingId ? '编辑动作' : '新增动作' }}</el-divider>
      <el-form :model="actionForm" label-width="80px" inline>
        <el-form-item label="设备">
          <el-select v-model="actionForm.device_id" filterable style="width: 200px" @change="onActionDevice">
            <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="控制点">
          <el-select v-model="actionForm.point_key" style="width: 150px" @change="onActionPoint">
            <el-option v-for="p in actionPoints" :key="p.point_key" :label="p.point_name" :value="p.point_key" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值">
          <el-select v-if="actionPoint?.point_type === 'enum'" v-model="actionForm.target_value" style="width: 130px">
            <el-option v-for="opt in actionPoint?.enum_options || []" :key="String(opt.value)" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-input-number v-else v-model="actionForm.target_value" :min="actionPoint?.value_min ?? undefined" :max="actionPoint?.value_max ?? undefined" style="width: 130px" />
        </el-form-item>
        <el-form-item label="延迟(秒)">
          <el-input-number v-model="actionForm.delay_sec" :min="0" style="width: 110px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitAction">保存</el-button>
          <el-button @click="resetActionForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 场景定时 -->
    <el-dialog v-model="scheduleDialog" :title="`场景定时 - ${currentScene?.scene_name || ''}`" width="480px">
      <el-form :model="scheduleForm" label-width="90px">
        <el-form-item label="Cron" required>
          <el-input v-model="scheduleForm.cron_expr" placeholder="分 时 日 月 周" />
          <div class="cron-presets">
            <el-tag
              v-for="c in CRON_PRESETS"
              :key="c.value"
              size="small"
              effect="plain"
              class="preset"
              @click="scheduleForm.cron_expr = c.value; scheduleForm.repeat_desc = c.label"
            >
              {{ c.label }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="重复说明"><el-input v-model="scheduleForm.repeat_desc" /></el-form-item>
        <el-form-item label="启用定时"><el-switch v-model="scheduleForm.enable_status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialog = false">取消</el-button>
        <el-button type="primary" @click="submitSchedule">保存</el-button>
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
