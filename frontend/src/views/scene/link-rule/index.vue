<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sceneApi, type LinkRuleItem } from '@/api/scene'
import { controlApi, type ControlDevice, type ControlPointItem } from '@/api/control'
import { pointApi, type PointItem } from '@/api/point'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const OPERATORS = [
  { label: '大于 >', value: '>' },
  { label: '大于等于 >=', value: '>=' },
  { label: '小于 <', value: '<' },
  { label: '小于等于 <=', value: '<=' },
  { label: '等于 ==', value: '==' },
  { label: '不等于 !=', value: '!=' },
]

const table = useTable<LinkRuleItem>(sceneApi.linkRules, { keyword: '', enable_status: undefined })
const scenes = ref<{ id: number; scene_name: string }[]>([])
const devices = ref<ControlDevice[]>([])
const points = ref<PointItem[]>([])

onMounted(async () => {
  table.load()
  const s = await sceneApi.list({ page: 1, page_size: 100 })
  scenes.value = s.items
  devices.value = await controlApi.points()
  const p = await pointApi.list({ page: 1, page_size: 200 })
  points.value = p.items
})

const dialog = ref(false)
const editingId = ref<number>()
const form = reactive<Record<string, any>>({})

const condPoints = computed(() => points.value.filter((p) => p.device_id === form.cond_device_id))
const actionPoints = computed<ControlPointItem[]>(
  () => devices.value.find((d) => d.device_id === form.target_device_id)?.points || [],
)

function openCreate() {
  editingId.value = undefined
  Object.assign(form, {
    rule_name: '',
    cond_device_id: undefined,
    cond_point_code: '',
    cond_operator: '>',
    cond_threshold: 0,
    action_type: 'scene',
    target_scene_id: undefined,
    target_device_id: undefined,
    target_point_key: '',
    target_value: '',
    enable_status: 1,
  })
  dialog.value = true
}
function openEdit(row: LinkRuleItem) {
  editingId.value = row.id
  const c = row.condition_json || {}
  Object.assign(form, {
    rule_name: row.rule_name,
    cond_device_id: c.device_id,
    cond_point_code: c.point_code,
    cond_operator: c.operator || '>',
    cond_threshold: c.threshold ?? 0,
    action_type: row.action_type || 'scene',
    target_scene_id: row.target_scene_id ?? undefined,
    target_device_id: row.target_device_id ?? undefined,
    target_point_key: row.target_point_key || '',
    target_value: row.target_value || '',
    enable_status: row.enable_status,
  })
  dialog.value = true
}
function onCondDevice() {
  form.cond_point_code = ''
}
function onTargetDevice() {
  form.target_point_key = ''
  form.target_value = ''
}

async function submit() {
  if (!form.rule_name) return ElMessage.warning('请填写规则名称')
  if (!form.cond_device_id || !form.cond_point_code) return ElMessage.warning('请选择触发设备与测点')
  if (form.action_type === 'scene' && !form.target_scene_id) return ElMessage.warning('请选择目标场景')
  if (form.action_type === 'control' && (!form.target_device_id || !form.target_point_key))
    return ElMessage.warning('请选择目标设备与控制点')

  const payload: Record<string, any> = {
    rule_name: form.rule_name,
    condition_text: `${form.cond_point_code} ${form.cond_operator} ${form.cond_threshold}`,
    condition_json: {
      device_id: form.cond_device_id,
      point_code: form.cond_point_code,
      operator: form.cond_operator,
      threshold: Number(form.cond_threshold),
    },
    action_type: form.action_type,
    enable_status: form.enable_status,
    target_scene_id: form.action_type === 'scene' ? form.target_scene_id : null,
    target_device_id: form.action_type === 'control' ? form.target_device_id : null,
    target_point_key: form.action_type === 'control' ? form.target_point_key : null,
    target_value: form.action_type === 'control' ? String(form.target_value) : null,
  }
  if (editingId.value) await sceneApi.updateLinkRule(editingId.value, payload)
  else await sceneApi.createLinkRule(payload)
  ElMessage.success('保存成功')
  dialog.value = false
  table.load()
}
async function remove(row: LinkRuleItem) {
  await ElMessageBox.confirm(`确认删除规则「${row.rule_name}」？`, '提示', { type: 'warning' })
  await sceneApi.removeLinkRule(row.id)
  ElMessage.success('删除成功')
  table.load()
}
async function toggleEnable(row: LinkRuleItem) {
  await sceneApi.setLinkEnable(row.id, row.enable_status)
  ElMessage.success('操作成功')
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>联动规则</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="规则名称" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.enable_status" placeholder="状态" clearable style="width: 120px" @change="table.search()">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
        <el-button type="primary" style="margin-left: auto" @click="openCreate">新增规则</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="rule_name" label="规则名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="condition_text" label="触发条件" min-width="180" show-overflow-tooltip />
        <el-table-column label="动作类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.action_type === 'scene' ? 'primary' : 'warning'">
              {{ row.action_type === 'scene' ? '触发场景' : '下发控制' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行目标" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.action_type === 'scene'">场景：{{ row.target_scene_name || '-' }}</span>
            <span v-else>设备：{{ row.target_device_name || '-' }} / {{ row.target_point_key }} = {{ row.target_value }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.enable_status" :active-value="1" :inactive-value="0" @change="toggleEnable(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
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

    <el-dialog v-model="dialog" :title="editingId ? '编辑联动规则' : '新增联动规则'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="规则名称" required><el-input v-model="form.rule_name" /></el-form-item>

        <el-divider content-position="left">触发条件</el-divider>
        <el-form-item label="触发设备" required>
          <el-select v-model="form.cond_device_id" filterable style="width: 100%" @change="onCondDevice">
            <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="监测测点" required>
          <el-select v-model="form.cond_point_code" filterable style="width: 100%">
            <el-option v-for="p in condPoints" :key="p.point_code" :label="`${p.point_name} (${p.point_code})`" :value="p.point_code" />
          </el-select>
        </el-form-item>
        <el-form-item label="判断条件" required>
          <el-select v-model="form.cond_operator" style="width: 150px">
            <el-option v-for="o in OPERATORS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-input-number v-model="form.cond_threshold" style="margin-left: 10px" />
        </el-form-item>

        <el-divider content-position="left">执行动作</el-divider>
        <el-form-item label="动作类型" required>
          <el-radio-group v-model="form.action_type">
            <el-radio value="scene">触发场景</el-radio>
            <el-radio value="control">下发控制</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.action_type === 'scene'" label="目标场景" required>
          <el-select v-model="form.target_scene_id" style="width: 100%">
            <el-option v-for="s in scenes" :key="s.id" :label="s.scene_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <template v-else>
          <el-form-item label="目标设备" required>
            <el-select v-model="form.target_device_id" filterable style="width: 100%" @change="onTargetDevice">
              <el-option v-for="d in devices" :key="d.device_id" :label="d.device_name" :value="d.device_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="控制点" required>
            <el-select v-model="form.target_point_key" style="width: 100%">
              <el-option v-for="p in actionPoints" :key="p.point_key" :label="p.point_name" :value="p.point_key" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标值" required><el-input v-model="form.target_value" /></el-form-item>
        </template>
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
