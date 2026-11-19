<script setup lang="ts">
import { onMounted } from 'vue'
import { accessApi, type AccessLogItem } from '@/api/device'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const table = useTable<AccessLogItem>(accessApi.logs, { keyword: '', action: undefined, result: undefined })

onMounted(() => table.load())
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备接入记录</h2></div>

      <div class="filter-bar">
        <el-input v-model="table.query.keyword" placeholder="设备名称 / 说明" clearable style="width: 200px" @keyup.enter="table.search()" />
        <el-select v-model="table.query.action" placeholder="操作类型" clearable style="width: 140px" @change="table.search()">
          <el-option label="接入" value="接入" />
          <el-option label="上线" value="上线" />
          <el-option label="下线" value="下线" />
          <el-option label="批量导入" value="批量导入" />
        </el-select>
        <el-select v-model="table.query.result" placeholder="结果" clearable style="width: 120px" @change="table.search()">
          <el-option label="成功" value="成功" />
          <el-option label="失败" value="失败" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="device_name" label="设备名称" min-width="170">
          <template #default="{ row }">{{ row.device_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="action" label="操作类型" width="110" />
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="row.result === '成功' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column prop="cost_ms" label="耗时(ms)" width="100" />
        <el-table-column label="操作时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.access_time) }}</template>
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
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
