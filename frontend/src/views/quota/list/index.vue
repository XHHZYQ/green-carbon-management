<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { quotaApi, type QuotaItem } from '@/api/quota'
import { energyTypeApi, type EnergyType } from '@/api/config'
import { areaApi, deviceApi, type AreaNode, type DeviceItem } from '@/api/device'
import { useTable } from '@/composables/useTable'

const table = useTable<QuotaItem>(quotaApi.quotas, {
  page_size: 10,
  quota_type: undefined,
  energy_type_id: undefined,
  period_type: undefined,
  keyword: '',
})

const energyTypeOptions = ref<EnergyType[]>([])
const areaTree = ref<AreaNode[]>([])
const deviceOptions = ref<DeviceItem[]>([])
const quotaOptions = ref<QuotaItem[]>([])

const quotaTypeOptions = [
  { label: '区域', value: 'area' },
  { label: '设备', value: 'device' },
  { label: '分项', value: 'item' },
]
const periodTypeOptions = [
  { label: '月度', value: 'month' },
  { label: '季度', value: 'quarter' },
  { label: '年度', value: 'year' },
]

/** 区域树拍平，便于下拉选择 */
const flatAreas = computed(() => {
  const out: { id: number; label: string }[] = []
  const walk = (nodes: AreaNode[], depth: number) => {
    for (const n of nodes) {
      out.push({ id: n.id, label: `${'　'.repeat(depth)}${n.area_name}` })
      if (n.children?.length) walk(n.children, depth + 1)
    }
  }
  walk(areaTree.value, 0)
  return out
})

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  quota_name: '',
  quota_type: 'area',
  energy_type_id: undefined as number | undefined | null,
  target_id: undefined as number | undefined | null,
  period_type: 'month',
  period_value: '',
  quota_value: undefined as number | undefined | null,
  unit: '',
  parent_id: undefined as number | undefined | null,
})
const formRef = ref<FormInstance>()

function quotaTypeLabel(value?: string | null) {
  return quotaTypeOptions.find((t) => t.value === value)?.label ?? '-'
}

function periodTypeLabel(value?: string | null) {
  return periodTypeOptions.find((t) => t.value === value)?.label ?? '-'
}

function energyTypeName(id?: number | null) {
  return energyTypeOptions.value.find((t) => t.id === id)?.type_name ?? '-'
}

function targetName(row: QuotaItem) {
  if (row.quota_type === 'area') {
    if (row.target_id === null || row.target_id === undefined) return '全园区'
    return flatAreas.value.find((a) => a.id === row.target_id)?.label.trim() ?? '-'
  }
  if (row.quota_type === 'device') {
    return deviceOptions.value.find((d) => d.id === row.target_id)?.device_name ?? '-'
  }
  return '-'
}

function parentName(row: QuotaItem) {
  return quotaOptions.value.find((q) => q.id === row.parent_id)?.quota_name ?? '-'
}

function openDialog(row?: QuotaItem) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    quota_name: row?.quota_name ?? '',
    quota_type: row?.quota_type ?? 'area',
    energy_type_id: row?.energy_type_id,
    target_id: row?.target_id,
    period_type: row?.period_type ?? 'month',
    period_value: row?.period_value ?? '',
    quota_value: row?.quota_value,
    unit: row?.unit ?? '',
    parent_id: row?.parent_id,
  })
  dialog.visible = true
}

function onQuotaTypeChange() {
  form.target_id = undefined
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    const payload = { ...form, period_value: form.period_value || null }
    if (dialog.edit && form.id) await quotaApi.updateQuota(form.id, payload)
    else await quotaApi.createQuota(payload)
    ElMessage.success('保存成功')
    dialog.visible = false
    await Promise.all([table.load(), loadQuotaOptions()])
  } finally {
    dialog.saving = false
  }
}

async function remove(row: QuotaItem) {
  await ElMessageBox.confirm(`确定删除定额「${row.quota_name}」吗？`, '提示', { type: 'warning' })
  await quotaApi.removeQuota(row.id!)
  ElMessage.success('删除成功')
  await Promise.all([table.load(), loadQuotaOptions()])
}

async function loadQuotaOptions() {
  const res = await quotaApi.quotas({ page: 1, page_size: 200 })
  quotaOptions.value = res.items
}

onMounted(async () => {
  await Promise.all([
    table.load(),
    energyTypeApi.list({ page: 1, page_size: 100 }).then((res) => (energyTypeOptions.value = res.items)),
    areaApi.tree().then((res) => (areaTree.value = res)),
    deviceApi.list({ page: 1, page_size: 200 }).then((res) => (deviceOptions.value = res.items)),
    loadQuotaOptions(),
  ])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>能耗定额管理</h2></div>

      <div class="filter-bar">
        <el-select v-model="table.query.quota_type" placeholder="定额类型" clearable style="width: 140px" @change="table.search()">
          <el-option v-for="t in quotaTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-select v-model="table.query.energy_type_id" placeholder="能源类型" clearable style="width: 160px" @change="table.search()">
          <el-option v-for="t in energyTypeOptions" :key="t.id" :label="t.type_name" :value="t.id!" />
        </el-select>
        <el-select v-model="table.query.period_type" placeholder="统计周期" clearable style="width: 140px" @change="table.search()">
          <el-option v-for="t in periodTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-input
          v-model="table.query.keyword"
          placeholder="定额名称"
          clearable
          style="width: 200px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <span />
        <el-button type="primary" @click="openDialog()">新增定额</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="quota_name" label="定额名称" min-width="200" />
        <el-table-column label="定额类型" width="100">
          <template #default="{ row }">{{ quotaTypeLabel(row.quota_type) }}</template>
        </el-table-column>
        <el-table-column label="能源类型" width="110">
          <template #default="{ row }">{{ energyTypeName(row.energy_type_id) }}</template>
        </el-table-column>
        <el-table-column label="定额对象" min-width="140">
          <template #default="{ row }">{{ targetName(row) }}</template>
        </el-table-column>
        <el-table-column label="统计周期" width="100">
          <template #default="{ row }">{{ periodTypeLabel(row.period_type) }}</template>
        </el-table-column>
        <el-table-column label="定额值" width="130">
          <template #default="{ row }">{{ row.quota_value }} {{ row.unit }}</template>
        </el-table-column>
        <el-table-column label="上级定额" min-width="180">
          <template #default="{ row }">{{ parentName(row) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
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

      <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑定额' : '新增定额'" width="560px">
        <el-form ref="formRef" :model="form" label-width="94px">
          <el-form-item label="定额名称" prop="quota_name" :rules="[{ required: true, message: '请输入定额名称' }]">
            <el-input v-model="form.quota_name" placeholder="如 A 栋厂房月度用电定额" />
          </el-form-item>
          <el-form-item label="定额类型">
            <el-select v-model="form.quota_type" style="width: 100%" @change="onQuotaTypeChange">
              <el-option v-for="t in quotaTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="能源类型">
            <el-select v-model="form.energy_type_id" placeholder="请选择能源类型" clearable style="width: 100%">
              <el-option v-for="t in energyTypeOptions" :key="t.id" :label="t.type_name" :value="t.id!" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.quota_type === 'area'" label="定额对象">
            <el-select v-model="form.target_id" placeholder="不选表示全园区" clearable style="width: 100%">
              <el-option v-for="a in flatAreas" :key="a.id" :label="a.label" :value="a.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-else-if="form.quota_type === 'device'" label="定额对象">
            <el-select v-model="form.target_id" placeholder="请选择设备" clearable filterable style="width: 100%">
              <el-option v-for="d in deviceOptions" :key="d.id" :label="d.device_name" :value="d.id!" />
            </el-select>
          </el-form-item>
          <el-form-item label="统计周期">
            <el-select v-model="form.period_type" style="width: 100%">
              <el-option v-for="t in periodTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="周期标识">
            <el-input v-model="form.period_value" placeholder="如 2026-10 或 2026" />
          </el-form-item>
          <el-form-item label="定额值" prop="quota_value" :rules="[{ required: true, message: '请输入定额值' }]">
            <el-input-number v-model="form.quota_value" :precision="2" :step="100" :min="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="单位">
            <el-input v-model="form.unit" placeholder="如 kWh、m³" />
          </el-form-item>
          <el-form-item label="上级定额">
            <el-select v-model="form.parent_id" placeholder="请选择上级定额" clearable style="width: 100%">
              <el-option
                v-for="q in quotaOptions.filter((x) => x.id !== form.id)"
                :key="q.id"
                :label="q.quota_name"
                :value="q.id!"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="dialog.saving" @click="submit">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
