<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { deviceApi, type DeviceDetail } from '@/api/device'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detail = ref<DeviceDetail>()

async function load() {
  loading.value = true
  try {
    detail.value = await deviceApi.detail(Number(route.query.id))
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-card" v-loading="loading">
      <div class="page-title">
        <h2>设备详情</h2>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-descriptions v-if="detail" :column="3" border>
        <el-descriptions-item label="设备编号">{{ detail.device_code }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ detail.device_name }}</el-descriptions-item>
        <el-descriptions-item label="设备类型">{{ detail.type_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="所属区域">{{ detail.area_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="通信协议">{{ detail.protocol_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="安装位置">{{ detail.install_location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="在线状态">
          <el-tag :type="detail.online_status === 'online' ? 'success' : 'info'" size="small">
            {{ detail.online_status === 'online' ? '在线' : '离线' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="接入时间">{{ formatDateTime(detail.access_time) }}</el-descriptions-item>
        <el-descriptions-item label="最近在线">{{ formatDateTime(detail.last_online_time) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-tabs v-if="detail" style="margin-top: 16px">
        <el-tab-pane label="连接参数">
          <el-table :data="detail.params" border size="small">
            <el-table-column prop="param_key" label="参数名" width="200" />
            <el-table-column prop="param_value" label="参数值" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`测点（${detail.points.length}）`">
          <el-table :data="detail.points" border size="small">
            <el-table-column prop="point_code" label="测点编码" width="160" />
            <el-table-column prop="point_name" label="测点名称" min-width="160" />
            <el-table-column prop="data_type" label="数据类型" width="100" />
            <el-table-column prop="unit" label="单位" width="90" />
            <el-table-column label="量程" width="150">
              <template #default="{ row }">{{ row.range_min ?? '-' }} ~ {{ row.range_max ?? '-' }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`采集任务（${detail.tasks.length}）`">
          <el-table :data="detail.tasks" border size="small">
            <el-table-column prop="task_name" label="任务名称" min-width="180" />
            <el-table-column label="采集方式" width="110">
              <template #default="{ row }">{{ row.collect_mode === 'period' ? '周期采集' : row.collect_mode }}</template>
            </el-table-column>
            <el-table-column prop="period_sec" label="周期(秒)" width="100" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.enable_status === 1 ? 'success' : 'info'" size="small">{{ row.enable_status === 1 ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最近执行" width="170">
              <template #default="{ row }">{{ formatDateTime(row.last_run_time) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>
