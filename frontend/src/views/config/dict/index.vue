<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  dictItemApi,
  dictTypeApi,
  energyItemApi,
  energyTypeApi,
  listSystemParams,
  saveSystemParams,
  type DictItem,
  type DictType,
  type EnergyItem,
  type EnergyType,
  type SystemParam,
} from '@/api/config'
import { useTable } from '@/composables/useTable'

const activeTab = ref('dict')

// ==================== 字典类型 ====================
const typeTable = useTable<DictType>(dictTypeApi.list, { keyword: '' })
const selectedType = ref<DictType | null>(null)
const typeDialog = reactive({ visible: false, edit: false, saving: false })
const typeForm = reactive({ id: undefined as number | undefined, type_code: '', type_name: '', remark: '', status: 1 })
const typeFormRef = ref<FormInstance>()

function openTypeDialog(row?: DictType) {
  typeDialog.edit = !!row
  Object.assign(typeForm, row ?? { type_code: '', type_name: '', remark: '', status: 1 })
  typeDialog.visible = true
}

async function submitType() {
  await typeFormRef.value?.validate()
  typeDialog.saving = true
  try {
    if (typeDialog.edit && typeForm.id) await dictTypeApi.update(typeForm.id, typeForm)
    else await dictTypeApi.create(typeForm)
    ElMessage.success('保存成功')
    typeDialog.visible = false
    await typeTable.load()
  } finally {
    typeDialog.saving = false
  }
}

async function removeType(row: DictType) {
  await ElMessageBox.confirm(`确定删除字典类型「${row.type_name}」吗？`, '提示', { type: 'warning' })
  await dictTypeApi.remove(row.id!)
  ElMessage.success('删除成功')
  if (selectedType.value?.id === row.id) selectedType.value = null
  await typeTable.load()
}

async function selectType(row: DictType) {
  selectedType.value = row
  itemTable.query.type_id = row.id
  await itemTable.search()
}

// ==================== 字典项 ====================
const itemTable = useTable<DictItem>(dictItemApi.list, { type_id: undefined, keyword: '' })
const itemDialog = reactive({ visible: false, edit: false, saving: false })
const itemForm = reactive({ id: undefined as number | undefined, item_label: '', item_value: '', sort_no: 0, status: 1, remark: '' })
const itemFormRef = ref<FormInstance>()

function openItemDialog(row?: DictItem) {
  itemDialog.edit = !!row
  Object.assign(itemForm, row ?? { item_label: '', item_value: '', sort_no: 0, status: 1, remark: '' })
  itemDialog.visible = true
}

async function submitItem() {
  await itemFormRef.value?.validate()
  itemDialog.saving = true
  try {
    const payload = { ...itemForm, type_id: selectedType.value?.id }
    if (itemDialog.edit && itemForm.id) await dictItemApi.update(itemForm.id, payload)
    else await dictItemApi.create(payload)
    ElMessage.success('保存成功')
    itemDialog.visible = false
    await itemTable.load()
  } finally {
    itemDialog.saving = false
  }
}

async function removeItem(row: DictItem) {
  await ElMessageBox.confirm(`确定删除字典项「${row.item_label}」吗？`, '提示', { type: 'warning' })
  await dictItemApi.remove(row.id!)
  ElMessage.success('删除成功')
  await itemTable.load()
}

// ==================== 系统参数 ====================
const paramsLoading = ref(false)
const params = ref<SystemParam[]>([])

async function loadParams() {
  paramsLoading.value = true
  try {
    params.value = await listSystemParams()
  } finally {
    paramsLoading.value = false
  }
}

async function submitParams() {
  await saveSystemParams(params.value)
  ElMessage.success('保存成功')
  await loadParams()
}

// ==================== 能源类型 ====================
const energyTypeTable = useTable<EnergyType>(energyTypeApi.list, { keyword: '' })
const etDialog = reactive({ visible: false, edit: false, saving: false })
const etForm = reactive({ id: undefined as number | undefined, type_code: '', type_name: '', unit: '', sort_no: 0, status: 1 })
const etFormRef = ref<FormInstance>()

function openEtDialog(row?: EnergyType) {
  etDialog.edit = !!row
  Object.assign(etForm, row ?? { type_code: '', type_name: '', unit: '', sort_no: 0, status: 1 })
  etDialog.visible = true
}

async function submitEt() {
  await etFormRef.value?.validate()
  etDialog.saving = true
  try {
    if (etDialog.edit && etForm.id) await energyTypeApi.update(etForm.id, etForm)
    else await energyTypeApi.create(etForm)
    ElMessage.success('保存成功')
    etDialog.visible = false
    await energyTypeTable.load()
  } finally {
    etDialog.saving = false
  }
}

async function removeEt(row: EnergyType) {
  await ElMessageBox.confirm(`确定删除能源类型「${row.type_name}」吗？`, '提示', { type: 'warning' })
  await energyTypeApi.remove(row.id!)
  ElMessage.success('删除成功')
  await energyTypeTable.load()
}

// ==================== 能耗分项 ====================
const energyItemTable = useTable<EnergyItem>(energyItemApi.list, { keyword: '' })
const energyTypeOptions = ref<EnergyType[]>([])
const eiDialog = reactive({ visible: false, edit: false, saving: false })
const eiForm = reactive({
  id: undefined as number | undefined,
  item_code: '',
  item_name: '',
  energy_type_id: undefined as number | undefined | null,
  sort_no: 0,
  status: 1,
})
const eiFormRef = ref<FormInstance>()

async function loadEnergyTypeOptions() {
  const res = await energyTypeApi.list({ page: 1, page_size: 100 })
  energyTypeOptions.value = res.items
}

function openEiDialog(row?: EnergyItem) {
  eiDialog.edit = !!row
  Object.assign(eiForm, row ?? { item_code: '', item_name: '', energy_type_id: undefined, sort_no: 0, status: 1 })
  eiDialog.visible = true
}

async function submitEi() {
  await eiFormRef.value?.validate()
  eiDialog.saving = true
  try {
    if (eiDialog.edit && eiForm.id) await energyItemApi.update(eiForm.id, eiForm)
    else await energyItemApi.create(eiForm)
    ElMessage.success('保存成功')
    eiDialog.visible = false
    await energyItemTable.load()
  } finally {
    eiDialog.saving = false
  }
}

async function removeEi(row: EnergyItem) {
  await ElMessageBox.confirm(`确定删除分项「${row.item_name}」吗？`, '提示', { type: 'warning' })
  await energyItemApi.remove(row.id!)
  ElMessage.success('删除成功')
  await energyItemTable.load()
}

function energyTypeName(id?: number | null) {
  return energyTypeOptions.value.find((t) => t.id === id)?.type_name ?? '-'
}

onMounted(async () => {
  await typeTable.load()
  await loadParams()
  await energyTypeTable.load()
  await loadEnergyTypeOptions()
  await energyItemTable.load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>数据字典</h2></div>
      <el-tabs v-model="activeTab">
        <!-- 字典类型 + 字典项 -->
        <el-tab-pane label="字典类型项" name="dict">
          <el-row :gutter="16">
            <el-col :span="11">
              <div class="table-toolbar">
                <el-input
                  v-model="typeTable.query.keyword"
                  placeholder="字典编码 / 名称"
                  clearable
                  style="width: 220px"
                  @keyup.enter="typeTable.search()"
                />
                <el-button type="primary" @click="openTypeDialog()">新增</el-button>
              </div>
              <el-table
                v-loading="typeTable.loading"
                :data="typeTable.list"
                border
                highlight-current-row
                height="420"
                @row-click="selectType"
              >
                <el-table-column prop="type_code" label="字典编码" min-width="130" />
                <el-table-column prop="type_name" label="字典名称" min-width="130" />
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                      {{ row.status === 1 ? '启用' : '停用' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="130" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click.stop="openTypeDialog(row)">编辑</el-button>
                    <el-button link type="danger" @click.stop="removeType(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-col>
            <el-col :span="13">
              <div class="table-toolbar">
                <span class="sub-title">
                  字典项{{ selectedType ? `：${selectedType.type_name}` : '（请先选择左侧字典类型）' }}
                </span>
                <el-button type="primary" :disabled="!selectedType" @click="openItemDialog()">新增</el-button>
              </div>
              <el-table v-loading="itemTable.loading" :data="itemTable.list" border height="420">
                <el-table-column prop="item_label" label="标签" min-width="120" />
                <el-table-column prop="item_value" label="值" min-width="120" />
                <el-table-column prop="sort_no" label="排序" width="70" />
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                      {{ row.status === 1 ? '启用' : '停用' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="130" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="openItemDialog(row)">编辑</el-button>
                    <el-button link type="danger" @click="removeItem(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 系统参数 -->
        <el-tab-pane label="系统参数" name="param">
          <div class="table-toolbar">
            <span class="sub-title">系统运行参数，修改后点击保存生效</span>
            <el-button type="primary" @click="submitParams">保存</el-button>
          </div>
          <el-table v-loading="paramsLoading" :data="params" border>
            <el-table-column prop="param_name" label="参数名称" min-width="150" />
            <el-table-column prop="param_key" label="参数键" min-width="170" />
            <el-table-column label="参数值" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.param_value" placeholder="请输入参数值" />
              </template>
            </el-table-column>
            <el-table-column prop="param_group" label="分组" width="120" />
            <el-table-column prop="remark" label="说明" min-width="180" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <!-- 能源类型 -->
        <el-tab-pane label="能源类型" name="energyType">
          <div class="table-toolbar">
            <el-input
              v-model="energyTypeTable.query.keyword"
              placeholder="编码 / 名称"
              clearable
              style="width: 220px"
              @keyup.enter="energyTypeTable.search()"
            />
            <el-button type="primary" @click="openEtDialog()">新增</el-button>
          </div>
          <el-table v-loading="energyTypeTable.loading" :data="energyTypeTable.list" border>
            <el-table-column prop="type_code" label="能源编码" min-width="120" />
            <el-table-column prop="type_name" label="能源名称" min-width="140" />
            <el-table-column prop="unit" label="计量单位" width="110" />
            <el-table-column prop="sort_no" label="排序" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                  {{ row.status === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEtDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeEt(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 能耗分项 -->
        <el-tab-pane label="能耗分项" name="energyItem">
          <div class="table-toolbar">
            <el-input
              v-model="energyItemTable.query.keyword"
              placeholder="分项编码 / 名称"
              clearable
              style="width: 220px"
              @keyup.enter="energyItemTable.search()"
            />
            <el-button type="primary" @click="openEiDialog()">新增</el-button>
          </div>
          <el-table v-loading="energyItemTable.loading" :data="energyItemTable.list" border>
            <el-table-column prop="item_code" label="分项编码" min-width="120" />
            <el-table-column prop="item_name" label="分项名称" min-width="140" />
            <el-table-column label="能源类型" width="130">
              <template #default="{ row }">{{ energyTypeName(row.energy_type_id) }}</template>
            </el-table-column>
            <el-table-column prop="sort_no" label="排序" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                  {{ row.status === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEiDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeEi(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 字典类型表单 -->
    <el-dialog v-model="typeDialog.visible" :title="typeDialog.edit ? '编辑字典类型' : '新增字典类型'" width="460px">
      <el-form ref="typeFormRef" :model="typeForm" label-width="90px">
        <el-form-item label="字典编码" prop="type_code" :rules="[{ required: true, message: '请输入字典编码' }]">
          <el-input v-model="typeForm.type_code" :disabled="typeDialog.edit" placeholder="如 energy_unit" />
        </el-form-item>
        <el-form-item label="字典名称" prop="type_name" :rules="[{ required: true, message: '请输入字典名称' }]">
          <el-input v-model="typeForm.type_name" placeholder="如 能源单位" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="typeForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="typeForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="typeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="typeDialog.saving" @click="submitType">确定</el-button>
      </template>
    </el-dialog>

    <!-- 字典项表单 -->
    <el-dialog v-model="itemDialog.visible" :title="itemDialog.edit ? '编辑字典项' : '新增字典项'" width="460px">
      <el-form ref="itemFormRef" :model="itemForm" label-width="90px">
        <el-form-item label="标签" prop="item_label" :rules="[{ required: true, message: '请输入标签' }]">
          <el-input v-model="itemForm.item_label" />
        </el-form-item>
        <el-form-item label="值" prop="item_value" :rules="[{ required: true, message: '请输入值' }]">
          <el-input v-model="itemForm.item_value" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="itemForm.sort_no" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="itemForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="itemForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="itemDialog.saving" @click="submitItem">确定</el-button>
      </template>
    </el-dialog>

    <!-- 能源类型表单 -->
    <el-dialog v-model="etDialog.visible" :title="etDialog.edit ? '编辑能源类型' : '新增能源类型'" width="460px">
      <el-form ref="etFormRef" :model="etForm" label-width="90px">
        <el-form-item label="能源编码" prop="type_code" :rules="[{ required: true, message: '请输入能源编码' }]">
          <el-input v-model="etForm.type_code" :disabled="etDialog.edit" placeholder="如 electricity" />
        </el-form-item>
        <el-form-item label="能源名称" prop="type_name" :rules="[{ required: true, message: '请输入能源名称' }]">
          <el-input v-model="etForm.type_name" placeholder="如 电力" />
        </el-form-item>
        <el-form-item label="计量单位">
          <el-input v-model="etForm.unit" placeholder="如 kWh" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="etForm.sort_no" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="etForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="etDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="etDialog.saving" @click="submitEt">确定</el-button>
      </template>
    </el-dialog>

    <!-- 能耗分项表单 -->
    <el-dialog v-model="eiDialog.visible" :title="eiDialog.edit ? '编辑分项' : '新增分项'" width="460px">
      <el-form ref="eiFormRef" :model="eiForm" label-width="90px">
        <el-form-item label="分项编码" prop="item_code" :rules="[{ required: true, message: '请输入分项编码' }]">
          <el-input v-model="eiForm.item_code" :disabled="eiDialog.edit" />
        </el-form-item>
        <el-form-item label="分项名称" prop="item_name" :rules="[{ required: true, message: '请输入分项名称' }]">
          <el-input v-model="eiForm.item_name" />
        </el-form-item>
        <el-form-item label="能源类型">
          <el-select v-model="eiForm.energy_type_id" placeholder="请选择" clearable style="width: 100%">
            <el-option v-for="t in energyTypeOptions" :key="t.id" :label="t.type_name" :value="t.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="eiForm.sort_no" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="eiForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="eiDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="eiDialog.saving" @click="submitEi">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.sub-title {
  font-size: 14px;
  color: $text-regular;
  line-height: 32px;
}
</style>
