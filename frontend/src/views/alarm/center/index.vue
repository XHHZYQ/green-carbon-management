<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  alarmApi,
  type AlarmInfoItem,
  type AlarmRuleItem,
  type AlarmStatistics,
} from '@/api/alarm'
import { deviceApi, type DeviceItem } from '@/api/device'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

// ---------------- 统计与趋势 ----------------
const statistics = ref<AlarmStatistics | null>(null)
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderTrend() {
  if (!chartRef.value || !statistics.value) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 30, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false, data: statistics.value.trend.days },
    yAxis: { type: 'value', name: '条', minInterval: 1 },
    series: [
      {
        name: '新增告警',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        itemStyle: { color: '#1677ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(22,119,255,0.28)' },
            { offset: 1, color: 'rgba(22,119,255,0.02)' },
          ]),
        },
        data: statistics.value.trend.values,
      },
    ],
  })
}

async function loadStatistics() {
  statistics.value = await alarmApi.statistics()
  renderTrend()
}

// ---------------- 告警列表 ----------------
const activeTab = ref('info')
const alarmTable = useTable<AlarmInfoItem>(alarmApi.infos, {
  level: undefined,
  status: undefined,
  alarm_type: undefined,
  keyword: '',
})

const levelOptions = [
  { label: '紧急', value: 'critical', tag: 'danger' as const },
  { label: '重要', value: 'major', tag: 'warning' as const },
  { label: '次要', value: 'minor', tag: 'primary' as const },
  { label: '提示', value: 'info', tag: 'info' as const },
]
const statusOptions = [
  { label: '待确认', value: 'pending', tag: 'danger' as const },
  { label: '已确认', value: 'confirmed', tag: 'warning' as const },
  { label: '已处理', value: 'handled', tag: 'success' as const },
  { label: '已忽略', value: 'ignored', tag: 'info' as const },
]
const typeOptions = ['越限', '离线', '故障', '通信', '温度'].map((v) => ({ label: v, value: v }))

function levelLabel(v?: string | null) {
  return levelOptions.find((x) => x.value === v)?.label ?? v ?? '-'
}
function levelTag(v?: string | null) {
  return levelOptions.find((x) => x.value === v)?.tag ?? 'info'
}
function statusLabel(v?: string | null) {
  return statusOptions.find((x) => x.value === v)?.label ?? v ?? '-'
}
function statusTag(v?: string | null) {
  return statusOptions.find((x) => x.value === v)?.tag ?? 'info'
}

const detail = reactive({ visible: false, loading: false, data: null as AlarmInfoItem | null })

async function openDetail(row: AlarmInfoItem) {
  detail.loading = true
  detail.visible = true
  try {
    detail.data = await alarmApi.getInfo(row.id)
  } finally {
    detail.loading = false
  }
}

async function reload() {
  await Promise.all([alarmTable.load(), loadStatistics()])
}

async function doConfirm(row: AlarmInfoItem) {
  await ElMessageBox.confirm(`确定确认告警「${row.alarm_no}」吗？`, '提示', { type: 'warning' })
  await alarmApi.confirm(row.id)
  ElMessage.success('确认成功')
  await reload()
}

async function doHandle(row: AlarmInfoItem) {
  await ElMessageBox.confirm(`确定将该告警标记为已处理吗？`, '提示', { type: 'warning' })
  await alarmApi.handle(row.id)
  ElMessage.success('处理成功')
  await reload()
}

async function doWorkOrder(row: AlarmInfoItem) {
  await ElMessageBox.confirm(`确定将告警「${row.alarm_no}」转为工单吗？`, '提示', { type: 'warning' })
  await alarmApi.toWorkOrder(row.id)
  ElMessage.success('工单已生成')
}

// ---------------- 告警规则 ----------------
const ruleTable = useTable<AlarmRuleItem>(alarmApi.rules.list, { keyword: '' })
const deviceOptions = ref<DeviceItem[]>([])
const ruleDialog = reactive({ visible: false, edit: false, saving: false })
const ruleForm = reactive({
  id: undefined as number | undefined,
  rule_name: '',
  rule_type: '越限',
  device_id: undefined as number | undefined | null,
  operator: 'gt',
  threshold: undefined as number | undefined | null,
  duration_sec: 60,
  alarm_level: 'major',
  enable_status: 1,
})
const ruleFormRef = ref<FormInstance>()

const operatorOptions = [
  { label: '大于', value: 'gt' },
  { label: '小于', value: 'lt' },
  { label: '等于', value: 'eq' },
  { label: '区间', value: 'range' },
]

function openRuleDialog(row?: AlarmRuleItem) {
  ruleDialog.edit = !!row
  Object.assign(ruleForm, {
    id: row?.id,
    rule_name: row?.rule_name ?? '',
    rule_type: row?.rule_type ?? '越限',
    device_id: row?.device_id ?? undefined,
    operator: row?.operator ?? 'gt',
    threshold: row?.threshold ?? undefined,
    duration_sec: row?.duration_sec ?? 60,
    alarm_level: row?.alarm_level ?? 'major',
    enable_status: row?.enable_status ?? 1,
  })
  ruleDialog.visible = true
}

async function submitRule() {
  await ruleFormRef.value?.validate()
  ruleDialog.saving = true
  try {
    if (ruleDialog.edit && ruleForm.id) await alarmApi.rules.update(ruleForm.id, ruleForm)
    else await alarmApi.rules.create(ruleForm)
    ElMessage.success('保存成功')
    ruleDialog.visible = false
    await ruleTable.load()
  } finally {
    ruleDialog.saving = false
  }
}

async function removeRule(row: AlarmRuleItem) {
  await ElMessageBox.confirm(`确定删除告警规则「${row.rule_name}」吗？`, '提示', { type: 'warning' })
  await alarmApi.rules.remove(row.id!)
  ElMessage.success('删除成功')
  await ruleTable.load()
}

async function loadDevices() {
  const res = await deviceApi.list({ page: 1, page_size: 200 })
  deviceOptions.value = res.items
}

function handleResize() {
  chart?.resize()
}

onMounted(async () => {
  await Promise.all([alarmTable.load(), loadStatistics(), loadDevices()])
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
      <el-col :xs="24" :sm="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ statistics?.total ?? 0 }}</div>
            <div class="stat-label">告警总数</div>
          </div>
          <div class="stat-icon">总</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ statistics?.pending ?? 0 }}</div>
            <div class="stat-label">待确认告警</div>
          </div>
          <div class="stat-icon">待</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="stat-card">
          <div>
            <div class="stat-value">{{ statistics?.today ?? 0 }}</div>
            <div class="stat-label">今日新增告警</div>
          </div>
          <div class="stat-icon">今</div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card row-gap">
      <div class="page-title"><h2>近 7 天告警趋势</h2></div>
      <div ref="chartRef" class="chart" />
    </div>

    <div class="page-card row-gap">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="告警列表" name="info">
          <div class="filter-bar">
            <el-select v-model="alarmTable.query.level" placeholder="告警等级" clearable style="width: 140px" @change="alarmTable.search()">
              <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
            </el-select>
            <el-select v-model="alarmTable.query.status" placeholder="状态" clearable style="width: 140px" @change="alarmTable.search()">
              <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
            <el-select v-model="alarmTable.query.alarm_type" placeholder="告警类型" clearable style="width: 140px" @change="alarmTable.search()">
              <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-input
              v-model="alarmTable.query.keyword"
              placeholder="告警编号 / 内容"
              clearable
              style="width: 220px"
              @keyup.enter="alarmTable.search()"
            />
            <el-button type="primary" @click="alarmTable.search()">查询</el-button>
            <el-button @click="alarmTable.reset()">重置</el-button>
          </div>

          <el-table v-loading="alarmTable.loading" :data="alarmTable.list" border>
            <el-table-column prop="alarm_no" label="告警编号" width="180" />
            <el-table-column prop="device_name" label="设备" min-width="150" />
            <el-table-column label="类型" width="90">
              <template #default="{ row }">{{ row.alarm_type || '-' }}</template>
            </el-table-column>
            <el-table-column label="等级" width="90">
              <template #default="{ row }">
                <el-tag :type="levelTag(row.alarm_level)" size="small">{{ levelLabel(row.alarm_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="告警时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.alarm_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">详情</el-button>
                <el-button v-if="row.status === 'pending'" link type="primary" @click="doConfirm(row)">确认</el-button>
                <el-button
                  v-if="row.status === 'confirmed'"
                  link
                  type="success"
                  @click="doHandle(row)"
                >处理</el-button>
                <el-button
                  v-if="row.status === 'confirmed' || row.status === 'handled'"
                  link
                  type="warning"
                  @click="doWorkOrder(row)"
                >转工单</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="table-pagination"
            :current-page="alarmTable.query.page"
            :page-size="alarmTable.query.page_size"
            :total="alarmTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="alarmTable.changePage"
            @size-change="alarmTable.changeSize"
          />
        </el-tab-pane>

        <el-tab-pane label="告警规则" name="rule">
          <div class="table-toolbar">
            <el-input
              v-model="ruleTable.query.keyword"
              placeholder="规则名称"
              clearable
              style="width: 220px"
              @keyup.enter="ruleTable.search()"
            />
            <el-button type="primary" @click="openRuleDialog()">新增规则</el-button>
          </div>

          <el-table v-loading="ruleTable.loading" :data="ruleTable.list" border>
            <el-table-column prop="rule_name" label="规则名称" min-width="180" />
            <el-table-column label="规则类型" width="100">
              <template #default="{ row }">{{ row.rule_type || '-' }}</template>
            </el-table-column>
            <el-table-column label="设备" min-width="150">
              <template #default="{ row }">{{ deviceOptions.find((d) => d.id === row.device_id)?.device_name ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="比较符" width="90">
              <template #default="{ row }">{{ operatorOptions.find((o) => o.value === row.operator)?.label ?? row.operator ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="阈值" width="100">
              <template #default="{ row }">{{ row.threshold ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="持续(秒)" width="100">
              <template #default="{ row }">{{ row.duration_sec ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="等级" width="90">
              <template #default="{ row }">
                <el-tag :type="levelTag(row.alarm_level)" size="small">{{ levelLabel(row.alarm_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.enable_status === 1 ? 'success' : 'info'" size="small">
                  {{ row.enable_status === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRuleDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="table-pagination"
            :current-page="ruleTable.query.page"
            :page-size="ruleTable.query.page_size"
            :total="ruleTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="ruleTable.changePage"
            @size-change="ruleTable.changeSize"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-drawer v-model="detail.visible" title="告警详情" size="480px">
      <el-descriptions v-if="detail.data" :column="1" border v-loading="detail.loading">
        <el-descriptions-item label="告警编号">{{ detail.data.alarm_no }}</el-descriptions-item>
        <el-descriptions-item label="设备">{{ detail.data.device_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="规则">{{ detail.data.rule_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="告警类型">{{ detail.data.alarm_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="告警等级">
          <el-tag :type="levelTag(detail.data.alarm_level)" size="small">{{ levelLabel(detail.data.alarm_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="告警值 / 阈值">
          {{ detail.data.alarm_value ?? '-' }} / {{ detail.data.threshold ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="内容">{{ detail.data.content || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(detail.data.status)" size="small">{{ statusLabel(detail.data.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="确认人">{{ detail.data.confirm_user_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="确认时间">{{ formatDateTime(detail.data.confirm_time) }}</el-descriptions-item>
        <el-descriptions-item label="告警时间">{{ formatDateTime(detail.data.alarm_time) }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <el-dialog v-model="ruleDialog.visible" :title="ruleDialog.edit ? '编辑告警规则' : '新增告警规则'" width="560px">
      <el-form ref="ruleFormRef" :model="ruleForm" label-width="100px">
        <el-form-item label="规则名称" prop="rule_name" :rules="[{ required: true, message: '请输入规则名称' }]">
          <el-input v-model="ruleForm.rule_name" placeholder="如 配电柜电流越限告警" />
        </el-form-item>
        <el-form-item label="规则类型">
          <el-select v-model="ruleForm.rule_type" style="width: 100%">
            <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联设备">
          <el-select v-model="ruleForm.device_id" placeholder="请选择设备" clearable filterable style="width: 100%">
            <el-option v-for="d in deviceOptions" :key="d.id" :label="d.device_name" :value="d.id!" />
          </el-select>
        </el-form-item>
        <el-form-item label="比较符">
          <el-select v-model="ruleForm.operator" style="width: 100%">
            <el-option v-for="o in operatorOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值" prop="threshold" :rules="[{ required: true, message: '请输入阈值' }]">
          <el-input-number v-model="ruleForm.threshold" :precision="2" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="持续时长(秒)">
          <el-input-number v-model="ruleForm.duration_sec" :min="0" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="告警等级">
          <el-select v-model="ruleForm.alarm_level" style="width: 100%">
            <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="ruleForm.enable_status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="ruleDialog.saving" @click="submitRule">确定</el-button>
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
