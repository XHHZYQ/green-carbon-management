<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { reportApi, type ReportRecordItem, type ReportTemplateItem } from '@/api/report'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const reportTypeOptions = [
  { label: '日报', value: 'daily' },
  { label: '周报', value: 'weekly' },
  { label: '月报', value: 'monthly' },
  { label: '年报', value: 'yearly' },
  { label: '自定义', value: 'custom' },
]
const dataSourceOptions = [
  { label: '能耗', value: 'energy' },
  { label: '碳排', value: 'carbon' },
  { label: '费用', value: 'fee' },
  { label: '综合', value: 'comprehensive' },
]
const dimensionOptions = [
  { label: '按区域', value: 'area' },
  { label: '按分项', value: 'item' },
  { label: '按设备', value: 'device' },
]

const table = useTable<ReportRecordItem>(reportApi.records, {
  page_size: 10,
  report_name: '',
  report_type: undefined,
})

const templates = ref<ReportTemplateItem[]>([])

function typeLabel(v?: string | null) {
  return reportTypeOptions.find((t) => t.value === v)?.label ?? '-'
}
function sourceLabel(v?: string | null) {
  return dataSourceOptions.find((t) => t.value === v)?.label ?? '-'
}

// ---------------- 生成报表 ----------------
const genDialog = reactive({ visible: false, saving: false })
const genForm = reactive({
  template_id: undefined as number | undefined,
  report_name: '',
  report_type: 'monthly',
  range: [] as string[],
  file_type: 'excel',
})

function openGenerate() {
  Object.assign(genForm, {
    template_id: templates.value[0]?.id,
    report_name: '',
    report_type: templates.value[0]?.report_type ?? 'monthly',
    range: [],
    file_type: 'excel',
  })
  genDialog.visible = true
}

function onTemplateChange(id?: number) {
  const tpl = templates.value.find((t) => t.id === id)
  if (tpl?.report_type) genForm.report_type = tpl.report_type
}

async function submitGenerate() {
  if (!genForm.template_id) {
    ElMessage.warning('请选择报表模板')
    return
  }
  genDialog.saving = true
  try {
    await reportApi.generate({
      template_id: genForm.template_id,
      report_name: genForm.report_name || undefined,
      report_type: genForm.report_type,
      period_start: genForm.range[0] || null,
      period_end: genForm.range[1] || null,
      file_type: genForm.file_type,
    })
    ElMessage.success('报表生成成功')
    genDialog.visible = false
    await table.search()
  } finally {
    genDialog.saving = false
  }
}

// ---------------- 自定义报表 ----------------
const cusDialog = reactive({ visible: false, saving: false })
const cusForm = reactive({
  report_name: '',
  data_source: 'energy',
  dimension: 'area',
  range: [] as string[],
})
const cusFormRef = ref<FormInstance>()

function openCustom() {
  Object.assign(cusForm, { report_name: '', data_source: 'energy', dimension: 'area', range: [] })
  cusDialog.visible = true
}

async function submitCustom() {
  await cusFormRef.value?.validate()
  cusDialog.saving = true
  try {
    await reportApi.custom({
      report_name: cusForm.report_name,
      data_source: cusForm.data_source,
      dimension: cusForm.dimension,
      period_start: cusForm.range[0] || null,
      period_end: cusForm.range[1] || null,
    })
    ElMessage.success('自定义报表生成成功')
    cusDialog.visible = false
    await table.search()
  } finally {
    cusDialog.saving = false
  }
}

// ---------------- 导出 ----------------
async function exportRecord(row: ReportRecordItem, fileType: 'excel' | 'pdf') {
  const blob = await reportApi.exportRecord(row.id, fileType)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${row.report_name}.${fileType === 'pdf' ? 'pdf' : 'xlsx'}`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

// ---------------- 模板管理 ----------------
const tplDialog = reactive({ visible: false, loading: false })
const tplFormDialog = reactive({ visible: false, edit: false, saving: false })
const tplForm = reactive({
  id: undefined as number | undefined,
  template_code: '',
  template_name: '',
  report_type: 'monthly',
  data_source: 'energy',
  status: 1,
})
const tplFormRef = ref<FormInstance>()

async function loadTemplates() {
  tplDialog.loading = true
  try {
    templates.value = await reportApi.templates()
  } finally {
    tplDialog.loading = false
  }
}

async function openTemplates() {
  tplDialog.visible = true
  await loadTemplates()
}

function openTplForm(row?: ReportTemplateItem) {
  tplFormDialog.edit = !!row
  Object.assign(tplForm, {
    id: row?.id,
    template_code: row?.template_code ?? '',
    template_name: row?.template_name ?? '',
    report_type: row?.report_type ?? 'monthly',
    data_source: row?.data_source ?? 'energy',
    status: row?.status ?? 1,
  })
  tplFormDialog.visible = true
}

async function submitTplForm() {
  await tplFormRef.value?.validate()
  tplFormDialog.saving = true
  try {
    const payload = {
      template_code: tplForm.template_code,
      template_name: tplForm.template_name,
      report_type: tplForm.report_type,
      data_source: tplForm.data_source,
      status: tplForm.status,
    }
    if (tplFormDialog.edit && tplForm.id) await reportApi.updateTemplate(tplForm.id, payload)
    else await reportApi.createTemplate(payload)
    ElMessage.success('保存成功')
    tplFormDialog.visible = false
    await loadTemplates()
  } finally {
    tplFormDialog.saving = false
  }
}

async function removeTemplate(row: ReportTemplateItem) {
  await ElMessageBox.confirm(`确定删除模板「${row.template_name}」吗？`, '提示', { type: 'warning' })
  await reportApi.removeTemplate(row.id!)
  ElMessage.success('删除成功')
  await loadTemplates()
}

onMounted(async () => {
  await Promise.all([table.load(), loadTemplates()])
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>报表中心</h2></div>

      <div class="filter-bar">
        <el-input
          v-model="table.query.report_name"
          placeholder="报表名称"
          clearable
          style="width: 220px"
          @keyup.enter="table.search()"
        />
        <el-select v-model="table.query.report_type" placeholder="报表类型" clearable style="width: 150px" @change="table.search()">
          <el-option v-for="t in reportTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <div class="table-toolbar">
        <el-button @click="openTemplates">模板管理</el-button>
        <span>
          <el-button @click="openCustom">自定义报表</el-button>
          <el-button type="primary" @click="openGenerate">生成报表</el-button>
        </span>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="report_name" label="报表名称" min-width="240" show-overflow-tooltip />
        <el-table-column label="报表类型" width="100">
          <template #default="{ row }">{{ typeLabel(row.report_type) }}</template>
        </el-table-column>
        <el-table-column label="统计区间" width="220">
          <template #default="{ row }">{{ row.period_start }} ~ {{ row.period_end }}</template>
        </el-table-column>
        <el-table-column label="文件格式" width="100">
          <template #default="{ row }">{{ row.file_type === 'pdf' ? 'PDF' : 'Excel' }}</template>
        </el-table-column>
        <el-table-column label="生成状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.gen_status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.gen_status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.gen_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="exportRecord(row, 'excel')">导出 Excel</el-button>
            <el-button link type="primary" @click="exportRecord(row, 'pdf')">导出 PDF</el-button>
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

    <!-- 生成报表 -->
    <el-dialog v-model="genDialog.visible" title="生成报表" width="520px">
      <el-form label-width="92px">
        <el-form-item label="报表模板" required>
          <el-select v-model="genForm.template_id" style="width: 100%" @change="onTemplateChange">
            <el-option v-for="t in templates" :key="t.id" :label="`${t.template_name}（${typeLabel(t.report_type)}）`" :value="t.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="报表类型">
          <el-select v-model="genForm.report_type" style="width: 100%">
            <el-option v-for="t in reportTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计区间">
          <el-date-picker v-model="genForm.range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="文件格式">
          <el-radio-group v-model="genForm.file_type">
            <el-radio value="excel">Excel</el-radio>
            <el-radio value="pdf">PDF</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="报表名称">
          <el-input v-model="genForm.report_name" placeholder="留空则自动生成" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="genDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="genDialog.saving" @click="submitGenerate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 自定义报表 -->
    <el-dialog v-model="cusDialog.visible" title="自定义报表" width="520px">
      <el-form ref="cusFormRef" :model="cusForm" label-width="92px">
        <el-form-item label="报表名称" prop="report_name" :rules="[{ required: true, message: '请输入报表名称' }]">
          <el-input v-model="cusForm.report_name" placeholder="如 10 月各区域能耗分析" />
        </el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="cusForm.data_source" style="width: 100%">
            <el-option v-for="t in dataSourceOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计维度">
          <el-select v-model="cusForm.dimension" style="width: 100%">
            <el-option v-for="t in dimensionOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计区间">
          <el-date-picker v-model="cusForm.range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cusDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="cusDialog.saving" @click="submitCustom">确定</el-button>
      </template>
    </el-dialog>

    <!-- 模板管理 -->
    <el-dialog v-model="tplDialog.visible" title="报表模板管理" width="860px">
      <div class="table-toolbar">
        <span />
        <el-button type="primary" @click="openTplForm()">新增模板</el-button>
      </div>
      <el-table v-loading="tplDialog.loading" :data="templates" border max-height="420">
        <el-table-column prop="template_code" label="模板编码" width="170" />
        <el-table-column prop="template_name" label="模板名称" min-width="160" />
        <el-table-column label="报表类型" width="100">
          <template #default="{ row }">{{ typeLabel(row.report_type) }}</template>
        </el-table-column>
        <el-table-column label="数据源" width="90">
          <template #default="{ row }">{{ sourceLabel(row.data_source) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" @click="openTplForm(row)">编辑</el-button>
            <el-button link type="danger" @click="removeTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 模板表单 -->
    <el-dialog v-model="tplFormDialog.visible" :title="tplFormDialog.edit ? '编辑模板' : '新增模板'" width="480px">
      <el-form ref="tplFormRef" :model="tplForm" label-width="92px">
        <el-form-item label="模板编码" prop="template_code" :rules="[{ required: true, message: '请输入模板编码' }]">
          <el-input v-model="tplForm.template_code" placeholder="如 TPL_ENERGY_MONTHLY" />
        </el-form-item>
        <el-form-item label="模板名称" prop="template_name" :rules="[{ required: true, message: '请输入模板名称' }]">
          <el-input v-model="tplForm.template_name" placeholder="如 能耗月报" />
        </el-form-item>
        <el-form-item label="报表类型">
          <el-select v-model="tplForm.report_type" style="width: 100%">
            <el-option v-for="t in reportTypeOptions.filter((x) => x.value !== 'custom')" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="tplForm.data_source" style="width: 100%">
            <el-option v-for="t in dataSourceOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="tplForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tplFormDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="tplFormDialog.saving" @click="submitTplForm">确定</el-button>
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
