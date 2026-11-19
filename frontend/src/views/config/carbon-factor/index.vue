<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  carbonFactorApi,
  energyTypeApi,
  type CarbonFactor,
  type EnergyType,
} from '@/api/config'
import { useTable } from '@/composables/useTable'

const table = useTable<CarbonFactor>(carbonFactorApi.list, { keyword: '' })
const energyTypeOptions = ref<EnergyType[]>([])

const dialog = reactive({ visible: false, edit: false, saving: false })
const form = reactive({
  id: undefined as number | undefined,
  energy_type_id: undefined as number | undefined | null,
  factor_name: '',
  factor_value: undefined as number | undefined | null,
  factor_unit: '',
  scope: '',
  effective_date: '',
  expire_date: '',
  status: 1,
})
const formRef = ref<FormInstance>()

function energyTypeName(id?: number | null) {
  return energyTypeOptions.value.find((t) => t.id === id)?.type_name ?? '-'
}

function openDialog(row?: CarbonFactor) {
  dialog.edit = !!row
  Object.assign(form, {
    id: row?.id,
    energy_type_id: row?.energy_type_id,
    factor_name: row?.factor_name ?? '',
    factor_value: row?.factor_value,
    factor_unit: row?.factor_unit ?? '',
    scope: row?.scope ?? '',
    effective_date: row?.effective_date ?? '',
    expire_date: row?.expire_date ?? '',
    status: row?.status ?? 1,
  })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    if (dialog.edit && form.id) await carbonFactorApi.update(form.id, form)
    else await carbonFactorApi.create(form)
    ElMessage.success('保存成功')
    dialog.visible = false
    await table.load()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: CarbonFactor) {
  await ElMessageBox.confirm(`确定删除碳排因子「${row.factor_name}」吗？`, '提示', { type: 'warning' })
  await carbonFactorApi.remove(row.id!)
  ElMessage.success('删除成功')
  await table.load()
}

async function loadEnergyTypeOptions() {
  const res = await energyTypeApi.list({ page: 1, page_size: 100 })
  energyTypeOptions.value = res.items
}

onMounted(async () => {
  await Promise.all([table.load(), loadEnergyTypeOptions()])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>碳排因子管理</h2></div>

      <div class="table-toolbar">
        <el-input
          v-model="table.query.keyword"
          placeholder="因子名称"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-button type="primary" @click="openDialog()">新增</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column label="能源类型" width="120">
          <template #default="{ row }">{{ energyTypeName(row.energy_type_id) }}</template>
        </el-table-column>
        <el-table-column prop="factor_name" label="因子名称" min-width="160" />
        <el-table-column prop="factor_value" label="因子值" width="130" />
        <el-table-column prop="factor_unit" label="单位" width="130" />
        <el-table-column prop="scope" label="适用范围" width="110" />
        <el-table-column prop="effective_date" label="生效日期" width="130" />
        <el-table-column prop="expire_date" label="失效日期" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
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

      <el-dialog v-model="dialog.visible" :title="dialog.edit ? '编辑碳排因子' : '新增碳排因子'" width="520px">
        <el-form ref="formRef" :model="form" label-width="90px">
          <el-form-item label="能源类型">
            <el-select v-model="form.energy_type_id" placeholder="请选择能源类型" clearable style="width: 100%">
              <el-option v-for="t in energyTypeOptions" :key="t.id" :label="t.type_name" :value="t.id!" />
            </el-select>
          </el-form-item>
          <el-form-item label="因子名称" prop="factor_name" :rules="[{ required: true, message: '请输入因子名称' }]">
            <el-input v-model="form.factor_name" placeholder="如 电力碳排放因子" />
          </el-form-item>
          <el-form-item label="因子值" prop="factor_value" :rules="[{ required: true, message: '请输入因子值' }]">
            <el-input-number v-model="form.factor_value" :precision="6" :step="0.001" :min="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="单位">
            <el-input v-model="form.factor_unit" placeholder="如 tCO2/MWh" />
          </el-form-item>
          <el-form-item label="适用范围">
            <el-select v-model="form.scope" placeholder="请选择适用范围" clearable style="width: 100%">
              <el-option label="范围一" value="范围一" />
              <el-option label="范围二" value="范围二" />
              <el-option label="范围三" value="范围三" />
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
