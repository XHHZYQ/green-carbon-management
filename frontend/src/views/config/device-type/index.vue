<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  deviceTypeApi,
  protocolApi,
  protocolParamApi,
  type DeviceType,
  type Protocol,
  type ProtocolParam,
} from '@/api/config'
import { useTable } from '@/composables/useTable'

const activeTab = ref('device')

// ==================== 设备类型 ====================
const deviceTable = useTable<DeviceType>(deviceTypeApi.list, { keyword: '' })
const protocolOptions = ref<Protocol[]>([])

const dtDialog = reactive({ visible: false, edit: false, saving: false })
const dtForm = reactive({
  id: undefined as number | undefined,
  type_code: '',
  type_name: '',
  category: '',
  default_protocol_id: undefined as number | undefined | null,
  icon: '',
  sort_no: 0,
  status: 1,
})
const dtFormRef = ref<FormInstance>()

function protocolName(id?: number | null) {
  return protocolOptions.value.find((p) => p.id === id)?.protocol_name ?? '-'
}

function openDtDialog(row?: DeviceType) {
  dtDialog.edit = !!row
  Object.assign(dtForm, {
    id: row?.id,
    type_code: row?.type_code ?? '',
    type_name: row?.type_name ?? '',
    category: row?.category ?? '',
    default_protocol_id: row?.default_protocol_id,
    icon: row?.icon ?? '',
    sort_no: row?.sort_no ?? 0,
    status: row?.status ?? 1,
  })
  dtDialog.visible = true
}

async function submitDt() {
  await dtFormRef.value?.validate()
  dtDialog.saving = true
  try {
    if (dtDialog.edit && dtForm.id) await deviceTypeApi.update(dtForm.id, dtForm)
    else await deviceTypeApi.create(dtForm)
    ElMessage.success('保存成功')
    dtDialog.visible = false
    await deviceTable.load()
  } finally {
    dtDialog.saving = false
  }
}

async function removeDt(row: DeviceType) {
  await ElMessageBox.confirm(`确定删除设备类型「${row.type_name}」吗？`, '提示', { type: 'warning' })
  await deviceTypeApi.remove(row.id!)
  ElMessage.success('删除成功')
  await deviceTable.load()
}

// ==================== 通信协议 ====================
const protocolTable = useTable<Protocol>(protocolApi.list, { keyword: '' })

const ptDialog = reactive({ visible: false, edit: false, saving: false })
const ptForm = reactive({
  id: undefined as number | undefined,
  protocol_code: '',
  protocol_name: '',
  category: '',
  description: '',
  status: 1,
})
const ptFormRef = ref<FormInstance>()

function openPtDialog(row?: Protocol) {
  ptDialog.edit = !!row
  Object.assign(ptForm, {
    id: row?.id,
    protocol_code: row?.protocol_code ?? '',
    protocol_name: row?.protocol_name ?? '',
    category: row?.category ?? '',
    description: row?.description ?? '',
    status: row?.status ?? 1,
  })
  ptDialog.visible = true
}

async function submitPt() {
  await ptFormRef.value?.validate()
  ptDialog.saving = true
  try {
    if (ptDialog.edit && ptForm.id) await protocolApi.update(ptForm.id, ptForm)
    else await protocolApi.create(ptForm)
    ElMessage.success('保存成功')
    ptDialog.visible = false
    await protocolTable.load()
    await loadProtocolOptions()
  } finally {
    ptDialog.saving = false
  }
}

async function removePt(row: Protocol) {
  await ElMessageBox.confirm(`确定删除通信协议「${row.protocol_name}」吗？`, '提示', { type: 'warning' })
  await protocolApi.remove(row.id!)
  ElMessage.success('删除成功')
  await protocolTable.load()
  await loadProtocolOptions()
}

// ==================== 协议参数 ====================
const paramVisible = ref(false)
const currentProtocol = ref<Protocol | null>(null)
const paramLoading = ref(false)
const params = ref<ProtocolParam[]>([])

const pmDialog = reactive({ visible: false, edit: false, saving: false })
const pmForm = reactive({
  id: undefined as number | undefined,
  param_key: '',
  param_label: '',
  param_type: 'text',
  required: false,
  default_value: '',
  sort_no: 0,
})
const pmFormRef = ref<FormInstance>()

async function openParams(row: Protocol) {
  currentProtocol.value = row
  paramVisible.value = true
  await loadParams()
}

async function loadParams() {
  if (!currentProtocol.value?.id) return
  paramLoading.value = true
  try {
    const res = await protocolParamApi.list({ protocol_id: currentProtocol.value.id, page: 1, page_size: 100 })
    params.value = res.items
  } finally {
    paramLoading.value = false
  }
}

function openPmDialog(row?: ProtocolParam) {
  pmDialog.edit = !!row
  Object.assign(pmForm, {
    id: row?.id,
    param_key: row?.param_key ?? '',
    param_label: row?.param_label ?? '',
    param_type: row?.param_type ?? 'text',
    required: row?.required ?? false,
    default_value: row?.default_value ?? '',
    sort_no: row?.sort_no ?? 0,
  })
  pmDialog.visible = true
}

async function submitPm() {
  await pmFormRef.value?.validate()
  pmDialog.saving = true
  try {
    const payload = { ...pmForm, protocol_id: currentProtocol.value?.id }
    if (pmDialog.edit && pmForm.id) await protocolParamApi.update(pmForm.id, payload)
    else await protocolParamApi.create(payload)
    ElMessage.success('保存成功')
    pmDialog.visible = false
    await loadParams()
  } finally {
    pmDialog.saving = false
  }
}

async function removePm(row: ProtocolParam) {
  await ElMessageBox.confirm(`确定删除参数「${row.param_label}」吗？`, '提示', { type: 'warning' })
  await protocolParamApi.remove(row.id!)
  ElMessage.success('删除成功')
  await loadParams()
}

async function loadProtocolOptions() {
  const res = await protocolApi.list({ page: 1, page_size: 100 })
  protocolOptions.value = res.items
}

onMounted(async () => {
  await Promise.all([deviceTable.load(), protocolTable.load(), loadProtocolOptions()])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备类型与协议</h2></div>
      <el-tabs v-model="activeTab">
        <!-- 设备类型 -->
        <el-tab-pane label="设备类型" name="device">
          <div class="table-toolbar">
            <el-input
              v-model="deviceTable.query.keyword"
              placeholder="编码 / 名称"
              clearable
              style="width: 220px"
              @keyup.enter="deviceTable.search()"
            />
            <el-button type="primary" @click="openDtDialog()">新增</el-button>
          </div>
          <el-table v-loading="deviceTable.loading" :data="deviceTable.list" border>
            <el-table-column prop="type_code" label="类型编码" min-width="120" />
            <el-table-column prop="type_name" label="类型名称" min-width="140" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column label="默认协议" width="150">
              <template #default="{ row }">{{ protocolName(row.default_protocol_id) }}</template>
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
                <el-button link type="primary" @click="openDtDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeDt(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 通信协议 -->
        <el-tab-pane label="通信协议" name="protocol">
          <div class="table-toolbar">
            <el-input
              v-model="protocolTable.query.keyword"
              placeholder="编码 / 名称"
              clearable
              style="width: 220px"
              @keyup.enter="protocolTable.search()"
            />
            <el-button type="primary" @click="openPtDialog()">新增</el-button>
          </div>
          <el-table v-loading="protocolTable.loading" :data="protocolTable.list" border>
            <el-table-column prop="protocol_code" label="协议编码" min-width="120" />
            <el-table-column prop="protocol_name" label="协议名称" min-width="140" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                  {{ row.status === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openParams(row)">参数配置</el-button>
                <el-button link type="primary" @click="openPtDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removePt(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <!-- 设备类型表单 -->
      <el-dialog v-model="dtDialog.visible" :title="dtDialog.edit ? '编辑设备类型' : '新增设备类型'" width="520px">
        <el-form ref="dtFormRef" :model="dtForm" label-width="90px">
          <el-form-item label="类型编码" prop="type_code" :rules="[{ required: true, message: '请输入类型编码' }]">
            <el-input v-model="dtForm.type_code" placeholder="如 meter" />
          </el-form-item>
          <el-form-item label="类型名称" prop="type_name" :rules="[{ required: true, message: '请输入类型名称' }]">
            <el-input v-model="dtForm.type_name" placeholder="如 智能电表" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="dtForm.category" placeholder="如 计量设备" />
          </el-form-item>
          <el-form-item label="默认协议">
            <el-select v-model="dtForm.default_protocol_id" placeholder="请选择默认协议" clearable style="width: 100%">
              <el-option v-for="p in protocolOptions" :key="p.id" :label="p.protocol_name" :value="p.id!" />
            </el-select>
          </el-form-item>
          <el-form-item label="图标">
            <el-input v-model="dtForm.icon" placeholder="Element Plus 图标名，如 Monitor" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="dtForm.sort_no" :min="0" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="dtForm.status" :active-value="1" :inactive-value="0" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dtDialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="dtDialog.saving" @click="submitDt">确定</el-button>
        </template>
      </el-dialog>

      <!-- 通信协议表单 -->
      <el-dialog v-model="ptDialog.visible" :title="ptDialog.edit ? '编辑通信协议' : '新增通信协议'" width="520px">
        <el-form ref="ptFormRef" :model="ptForm" label-width="90px">
          <el-form-item label="协议编码" prop="protocol_code" :rules="[{ required: true, message: '请输入协议编码' }]">
            <el-input v-model="ptForm.protocol_code" placeholder="如 modbus_tcp" />
          </el-form-item>
          <el-form-item label="协议名称" prop="protocol_name" :rules="[{ required: true, message: '请输入协议名称' }]">
            <el-input v-model="ptForm.protocol_name" placeholder="如 Modbus TCP" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="ptForm.category" placeholder="如 有线 / 无线" />
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="ptForm.description" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="ptForm.status" :active-value="1" :inactive-value="0" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="ptDialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="ptDialog.saving" @click="submitPt">确定</el-button>
        </template>
      </el-dialog>

      <!-- 协议参数抽屉 -->
      <el-drawer v-model="paramVisible" :title="`协议参数：${currentProtocol?.protocol_name ?? ''}`" size="620px">
        <div class="table-toolbar">
          <span class="sub-title">定义该协议的采集参数模板</span>
          <el-button type="primary" @click="openPmDialog()">新增参数</el-button>
        </div>
        <el-table v-loading="paramLoading" :data="params" border>
          <el-table-column prop="param_key" label="参数键" min-width="130" />
          <el-table-column prop="param_label" label="参数名称" min-width="130" />
          <el-table-column prop="param_type" label="类型" width="100" />
          <el-table-column label="必填" width="70">
            <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column prop="default_value" label="默认值" min-width="110" />
          <el-table-column prop="sort_no" label="排序" width="70" />
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openPmDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="removePm(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-drawer>

      <!-- 协议参数表单 -->
      <el-dialog v-model="pmDialog.visible" :title="pmDialog.edit ? '编辑参数' : '新增参数'" width="480px" append-to-body>
        <el-form ref="pmFormRef" :model="pmForm" label-width="90px">
          <el-form-item label="参数键" prop="param_key" :rules="[{ required: true, message: '请输入参数键' }]">
            <el-input v-model="pmForm.param_key" placeholder="如 slave_id" />
          </el-form-item>
          <el-form-item label="参数名称" prop="param_label" :rules="[{ required: true, message: '请输入参数名称' }]">
            <el-input v-model="pmForm.param_label" placeholder="如 从站地址" />
          </el-form-item>
          <el-form-item label="参数类型">
            <el-select v-model="pmForm.param_type" style="width: 100%">
              <el-option label="文本" value="text" />
              <el-option label="数字" value="number" />
              <el-option label="布尔" value="boolean" />
              <el-option label="选择" value="select" />
            </el-select>
          </el-form-item>
          <el-form-item label="是否必填">
            <el-switch v-model="pmForm.required" />
          </el-form-item>
          <el-form-item label="默认值">
            <el-input v-model="pmForm.default_value" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="pmForm.sort_no" :min="0" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="pmDialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="pmDialog.saving" @click="submitPm">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>
