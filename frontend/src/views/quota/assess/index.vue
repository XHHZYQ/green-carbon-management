<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { quotaApi, type QuotaAssessItem, type QuotaReport } from '@/api/quota'
import { useTable } from '@/composables/useTable'
import { formatNumber } from '@/utils/format'

const currentYear = new Date().getFullYear()
const currentMonth = `${currentYear}-${String(new Date().getMonth() + 1).padStart(2, '0')}`

const report = ref<QuotaReport | null>(null)
const year = ref(currentYear)
const generatePeriod = ref(currentMonth)
const generating = ref(false)

const table = useTable<QuotaAssessItem>(quotaApi.assess, { page_size: 10, period_value: undefined })

const pieRef = ref<HTMLDivElement>()
const lineRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

const gradeColors: Record<string, string> = {
  A: '#00b96b',
  B: '#1677ff',
  C: '#faad14',
  D: '#f5222d',
}

const gradeTagMap: Record<string, 'success' | 'primary' | 'warning' | 'danger'> = {
  A: 'success',
  B: 'primary',
  C: 'warning',
  D: 'danger',
}

const resultTagMap: Record<string, 'success' | 'primary' | 'warning' | 'danger'> = {
  优秀: 'success',
  合格: 'primary',
  预警: 'warning',
  超标: 'danger',
}

function renderCharts() {
  if (!report.value) return
  if (pieRef.value) {
    pieChart = pieChart ?? echarts.init(pieRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          name: '考核等级',
          type: 'pie',
          radius: ['45%', '68%'],
          center: ['50%', '45%'],
          label: { formatter: '{b}: {c}' },
          data: report.value.grade_ratio.map((x) => ({
            name: `${x.name} 级`,
            value: x.value,
            itemStyle: { color: gradeColors[x.name] },
          })),
        },
      ],
    })
  }
  if (lineRef.value) {
    lineChart = lineChart ?? echarts.init(lineRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 24, top: 30, bottom: 30 },
      xAxis: { type: 'category', boundaryGap: false, data: report.value.score_trend.periods },
      yAxis: { type: 'value', name: '分', min: 0, max: 100 },
      series: [
        {
          name: '平均得分',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          itemStyle: { color: '#1677ff' },
          areaStyle: { color: 'rgba(22,119,255,0.12)' },
          data: report.value.score_trend.values,
        },
      ],
    })
  }
}

async function loadReport() {
  report.value = await quotaApi.report({ year: year.value })
  renderCharts()
}

async function doGenerate() {
  if (!generatePeriod.value) {
    ElMessage.warning('请选择考核周期')
    return
  }
  generating.value = true
  try {
    const res = await quotaApi.generateAssess({ period_value: generatePeriod.value })
    ElMessage.success(`考核生成完成，共 ${res.count} 条`)
    await Promise.all([table.search(), loadReport()])
  } finally {
    generating.value = false
  }
}

function handleResize() {
  pieChart?.resize()
  lineChart?.resize()
}

onMounted(async () => {
  await Promise.all([table.load(), loadReport()])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  lineChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="12" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ formatNumber(report?.cards.avg_score, 2) }}</div>
            <div class="stat-label">平均得分</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ report?.cards.a_count ?? 0 }}</div>
            <div class="stat-label">A 级定额数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ report?.cards.exceed_count ?? 0 }}</div>
            <div class="stat-label">超标定额数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :lg="6">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ report?.cards.assess_count ?? 0 }}</div>
            <div class="stat-label">考核总条数</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="10">
        <div class="page-card">
          <div class="page-title"><h2>等级分布</h2></div>
          <div ref="pieRef" class="chart" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="14">
        <div class="page-card">
          <div class="page-title"><h2>评分趋势</h2></div>
          <div ref="lineRef" class="chart" />
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title">
        <h2>定额考核</h2>
        <div style="display: flex; gap: 12px; align-items: center">
          <el-date-picker v-model="generatePeriod" type="month" value-format="YYYY-MM" placeholder="考核周期" style="width: 160px" />
          <el-button type="primary" :loading="generating" @click="doGenerate">生成考核</el-button>
        </div>
      </div>

      <div class="filter-bar">
        <el-date-picker
          v-model="table.query.period_value"
          type="month"
          value-format="YYYY-MM"
          placeholder="统计周期"
          clearable
          style="width: 180px"
          @change="table.search()"
        />
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="assess_name" label="考核名称" min-width="220" />
        <el-table-column prop="target_name" label="考核对象" min-width="140" />
        <el-table-column prop="period_value" label="周期" width="100" />
        <el-table-column label="定额值" width="120">
          <template #default="{ row }">{{ formatNumber(row.quota_value, 2) }}</template>
        </el-table-column>
        <el-table-column label="实际值" width="120">
          <template #default="{ row }">{{ formatNumber(row.actual_value, 2) }}</template>
        </el-table-column>
        <el-table-column label="得分" width="90">
          <template #default="{ row }">{{ formatNumber(row.score, 2) }}</template>
        </el-table-column>
        <el-table-column label="等级" width="80">
          <template #default="{ row }">
            <el-tag :type="gradeTagMap[row.grade] ?? 'info'" size="small">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="resultTagMap[row.assess_result] ?? 'info'" size="small">{{ row.assess_result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="考核时间" width="170">
          <template #default="{ row }">{{ row.assess_time }}</template>
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
