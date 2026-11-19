<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { priceApi, type PriceHistory, type PricePeriod, type PricePlan } from '@/api/price'
import { energyTypeApi, type EnergyType } from '@/api/config'

const loading = ref(false)
const list = ref<PricePlan[]>([])
const keyword = ref('')
const energyTypeOptions = ref<EnergyType[]>([])

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive<Partial<PricePlan>>({
  id: undefined,
  plan_code: '',
  plan_name: '',
  energy_type_id: undefined,
  effective_date: '',
  expire_date: '',
  status: 1,
})
const formRef = ref<FormInstance>()

const drawer = reactive({ visible: false, plan: null as PricePlan | null, tab: 'period' })
const periods = ref<PricePeriod[]>([])
const history = ref<PriceHistory[]>([])

const periodDialog = reactive({ visible: false, edit: false, saving: false })
const periodForm = reactive<Partial<PricePeriod>>({
  id: undefined,
  period_type: 'sharp',
  start_time: '',
  end_time: '',
  day_type: 'workday',
  price: undefined,
  sort_no: 0,
})
const periodFormRef = ref<FormInstance>()

const periodTypeOptions = [
  { label: '尖峰', value: 'sharp' },
  { label: '高峰', value: 'peak' },
  { label: '平段', value: 'flat' },
  { label: '低谷', value: 'valley' },
]
const dayTypeOptions = [
  { label: '工作日', value: 'workday' },
  { label: '周末', value: 'weekend' },
  { label: '节假日', value: 'holiday' },
]

async function load() {
  loading.value = true
  try {
    list.value = await priceApi.plans({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

function openPlanDialog(row?: PricePlan) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    plan_code: row?.plan_code ?? '',
    plan_name: row?.plan_name ?? '',
    energy_type_id: row?.energy_type_id ?? undefined,
    effective_date: row?.effective_date ?? '',
    expire_date: row?.expire_date ?? '',
    status: row?.status ?? 1,
  })
  dialog.visible = true
}

async function submitPlan() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    if (dialog.edit && form.id) await priceApi.updatePlan(form.id, form)
    else await priceApi.createPlan(form)
    ElMessage.success('保存成功')
    dialog.visible = false
    await load()
  } finally {
    dialog.saving = false
  }
}

async function removePlan(row: PricePlan) {
  await ElMessageBox.confirm(`确定删除电价方案「${row.plan_name}」吗？`, '提示', { type: 'warning' })
  await priceApi.removePlan(row.id!)
  ElMessage.success('删除成功')
  await load()
}

async function openDrawer(row: PricePlan) {
  drawer.plan = row
  drawer.tab = 'period'
  drawer.visible = true
  await Promise.all([loadPeriods(), loadHistory()])
}

async function loadPeriods() {
  if (!drawer.plan?.id) return
  periods.value = await priceApi.periods(drawer.plan.id)
}

async function loadHistory() {
  if (!drawer.plan?.id) return
  history.value = await priceApi.history(drawer.plan.id)
}

function openPeriodDialog(row?: PricePeriod) {
  periodDialog.edit = !!row
  Object.assign(periodForm, {
    id: row?.id,
    period_type: row?.period_type ?? 'sharp',
    start_time: row?.start_time ?? '',
    end_time: row?.end_time ?? '',
    day_type: row?.day_type ?? 'workday',
    price: row?.price,
    sort_no: row?.sort_no ?? 0,
  })
  periodDialog.visible = true
}

async function submitPeriod() {
  await periodFormRef.value?.validate()
  if (!drawer.plan?.id) return
  periodDialog.saving = true
  try {
    if (periodDialog.edit && periodForm.id) await priceApi.updatePeriod(periodForm.id, periodForm)
    else await priceApi.createPeriod(drawer.plan.id, periodForm)
    ElMessage.success('保存成功')
    periodDialog.visible = false
    await Promise.all([loadPeriods(), loadHistory()])
  } finally {
    periodDialog.saving = false
  }
}

async function removePeriod(row: PricePeriod) {
  await ElMessageBox.confirm(`确定删除该「${row.period_name}」时段吗？`, '提示', { type: 'warning' })
  await priceApi.removePeriod(row.id!)
  ElMessage.success('删除成功')
  await loadPeriods()
}

onMounted(async () => {
  const res = await energyTypeApi.list({ page: 1, page_size: 100 })
  energyTypeOptions.value = res.items
  await load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>电价方案</h2></div>

      <div class="table-toolbar">
        <el-input
          v-model="keyword"
          placeholder="方案名称"
          clearable
          style="width: 220px"
          @keyup.enter="load"
        />
        <el-button type="primary" @click="openPlanDialog()">新增方案</el-button>
      </div>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="plan_code" label="方案编码" width="140" />
        <el-table-column prop="plan_name" label="方案名称" min-width="180" />
        <el-table-column prop="energy_type_name" label="能源类型" width="110" />
        <el-table-column prop="effective_date" label="生效日期" width="120" />
        <el-table-column prop="expire_date" label="失效日期" width="120" />
        <el-table-column prop="period_count" label="时段数" width="90" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDrawer(row)">时段/历史</el-button>
            <el-button link type="primary" @click="openPlanDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="removePlan(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑电价方案' : '新增电价方案'" width="520px">
      <el-form ref="formRef" :model="form" label-width="90px">
        <el-form-item label="方案编码" prop="plan_code" :rules="[{ required: true, message: '请输入方案编码' }]">
          <el-input v-model="form.plan_code" placeholder="如 EPL2024" />
        </el-form-item>
        <el-form-item label="方案名称" prop="plan_name" :rules="[{ required: true, message: '请输入方案名称' }]">
          <el-input v-model="form.plan_name" placeholder="如 一般工商业电价方案" />
        </el-form-item>
        <el-form-item label="能源类型">
          <el-select v-model="form.energy_type_id" placeholder="请选择能源类型" clearable style="width: 100%">
            <el-option v-for="t in energyTypeOptions" :key="t.id" :label="t.type_name" :value="t.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="form.effective_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="失效日期">
          <el-date-picker v-model="form.expire_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="submitPlan">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="drawer.visible" :title="drawer.plan?.plan_name" size="720px">
      <el-tabs v-model="drawer.tab">
        <el-tab-pane label="时段划分" name="period">
          <div class="table-toolbar">
            <span />
            <el-button type="primary" size="small" @click="openPeriodDialog()">新增时段</el-button>
          </div>
          <el-table :data="periods" border>
            <el-table-column prop="period_name" label="时段" width="90" />
            <el-table-column prop="day_type_name" label="日期类型" width="100" />
            <el-table-column prop="start_time" label="开始" width="90" />
            <el-table-column prop="end_time" label="结束" width="90" />
            <el-table-column prop="price" label="电价(元/kWh)" width="130" />
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openPeriodDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removePeriod(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="调整历史" name="history">
          <el-table :data="history" border>
            <el-table-column prop="change_desc" label="变更说明" min-width="140" />
            <el-table-column prop="old_value" label="原值" width="90" />
            <el-table-column prop="new_value" label="新值" width="90" />
            <el-table-column prop="effective_date" label="生效日期" width="120" />
            <el-table-column prop="operator_name" label="操作人" width="100" />
            <el-table-column prop="changed_at" label="变更时间" width="170" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-dialog v-model="periodDialog.visible" :title="periodDialog.edit ? '编辑时段' : '新增时段'" width="480px">
      <el-form ref="periodFormRef" :model="periodForm" label-width="90px">
        <el-form-item label="时段类型" prop="period_type" :rules="[{ required: true, message: '请选择时段类型' }]">
          <el-select v-model="periodForm.period_type" style="width: 100%">
            <el-option v-for="p in periodTypeOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期类型">
          <el-select v-model="periodForm.day_type" style="width: 100%">
            <el-option v-for="d in dayTypeOptions" :key="d.value" :label="d.label" :value="d.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间" prop="start_time" :rules="[{ required: true, message: '请输入开始时间' }]">
          <el-time-picker v-model="periodForm.start_time" format="HH:mm" value-format="HH:mm" placeholder="开始时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time" :rules="[{ required: true, message: '请输入结束时间' }]">
          <el-time-picker v-model="periodForm.end_time" format="HH:mm" value-format="HH:mm" placeholder="结束时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="电价" prop="price" :rules="[{ required: true, message: '请输入电价' }]">
          <el-input-number v-model="periodForm.price" :precision="4" :step="0.01" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="periodForm.sort_no" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="periodDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="periodDialog.saving" @click="submitPeriod">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
