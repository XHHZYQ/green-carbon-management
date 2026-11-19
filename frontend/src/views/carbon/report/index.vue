<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, type FormInstance } from 'element-plus'
import { carbonApi, type CarbonReductionCompare, type CarbonReportItem } from '@/api/carbon'
import { useTable } from '@/composables/useTable'
import { formatNumber } from '@/utils/format'

const table = useTable<CarbonReportItem>(carbonApi.reports, { page_size: 10, report_type: undefined })
const compare = ref<CarbonReductionCompare | null>(null)
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const dialog = reactive({ visible: false, saving: false })
const form = reactive({
  report_name: '',
  report_type: 'yearly',
  period_start: '',
  period_end: '',
})
const formRef = ref<FormInstance>()

const reportTypeOptions = [
  { label: '年度报告', value: 'yearly' },
  { label: '季度报告', value: 'quarterly' },
  { label: '月度报告', value: 'monthly' },
  { label: '自定义', value: 'custom' },
]

function renderCompare() {
  if (!chartRef.value || !compare.value) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 60, right: 24, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: compare.value.type_compare.map((x) => x.name) },
    yAxis: { type: 'value', name: 'tCO2e' },
    series: [
      {
        name: '本年',
        type: 'bar',
        barWidth: 22,
        itemStyle: { color: '#00b96b', borderRadius: [4, 4, 0, 0] },
        data: compare.value.type_compare.map((x) => x.current),
      },
      {
        name: '去年',
        type: 'bar',
        barWidth: 22,
        itemStyle: { color: '#8fd9b3', borderRadius: [4, 4, 0, 0] },
        data: compare.value.type_compare.map((x) => x.last),
      },
    ],
  })
}

async function loadCompare() {
  compare.value = await carbonApi.reductionCompare()
  renderCompare()
}

function openDialog() {
  Object.assign(form, { report_name: '', report_type: 'yearly', period_start: '', period_end: '' })
  dialog.visible = true
}

async function submit() {
  await formRef.value?.validate()
  dialog.saving = true
  try {
    await carbonApi.createReport(form)
    ElMessage.success('报告生成成功')
    dialog.visible = false
    await table.search()
  } finally {
    dialog.saving = false
  }
}

async function doExport(row: CarbonReportItem) {
  const blob = await carbonApi.exportReport(row.id)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${row.report_name}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

function handleResize() {
  chart?.resize()
}

onMounted(async () => {
  await Promise.all([table.load(), loadCompare()])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(compare?.current_total, 2) }}</div>
            <div class="stat-label">{{ compare?.current_year }} 年碳排放 (tCO2e)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(compare?.pv_reduction, 2) }}</div>
            <div class="stat-label">光伏减排量 (tCO2e)</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ compare?.yoy_rate === null || compare?.yoy_rate === undefined ? '—' : `${compare?.yoy_rate}%` }}</div>
            <div class="stat-label">同比变化</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title"><h2>减排对比</h2></div>
      <div ref="chartRef" class="chart" />
    </div>

    <div class="page-card row-gap">
      <div class="page-title">
        <h2>碳报告</h2>
        <el-button type="primary" @click="openDialog">生成报告</el-button>
      </div>
      <div class="filter-bar">
        <el-select v-model="table.query.report_type" placeholder="报告类型" clearable style="width: 160px" @change="table.search()">
          <el-option v-for="t in reportTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="report_no" label="报告编号" width="160" />
        <el-table-column prop="report_name" label="报告名称" min-width="220" />
        <el-table-column prop="period_start" label="起始" width="120" />
        <el-table-column prop="period_end" label="结束" width="120" />
        <el-table-column label="总排放 (tCO2e)" min-width="130">
          <template #default="{ row }">{{ formatNumber(row.total_emission, 2) }}</template>
        </el-table-column>
        <el-table-column label="减排量 (tCO2e)" min-width="130">
          <template #default="{ row }">{{ formatNumber(row.reduction_value, 2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="doExport(row)">导出</el-button>
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

    <el-dialog v-model="dialog.visible" title="生成碳报告" width="520px">
      <el-form ref="formRef" :model="form" label-width="90px">
        <el-form-item label="报告名称" prop="report_name" :rules="[{ required: true, message: '请输入报告名称' }]">
          <el-input v-model="form.report_name" placeholder="如 2026年度园区碳排放核算报告" />
        </el-form-item>
        <el-form-item label="报告类型">
          <el-select v-model="form.report_type" style="width: 100%">
            <el-option v-for="t in reportTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计周期" prop="period_start" :rules="[{ required: true, message: '请选择统计周期' }]">
          <el-date-picker
            v-model="form.period_start"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
            @change="(val: string[] | null) => { if (val) { form.period_start = val[0]; form.period_end = val[1] } }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.chart {
  width: 100%;
  height: 300px;
}

.row-gap {
  margin-top: 16px;
}

.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
