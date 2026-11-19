<script setup lang="ts">
import { onMounted } from 'vue'
import { sceneApi, type SceneExecLogItem } from '@/api/scene'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const table = useTable<SceneExecLogItem>(sceneApi.execLogs, { exec_type: undefined, result: undefined })

onMounted(() => table.load())

function resultTag(result?: string | null) {
  if (result === 'success') return 'success'
  if (result === 'partial') return 'warning'
  return 'danger'
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>场景执行记录</h2></div>

      <div class="filter-bar">
        <el-select v-model="table.query.exec_type" placeholder="执行类型" clearable style="width: 160px" @change="table.search()">
          <el-option label="场景执行" value="scene" />
          <el-option label="联动触发" value="link" />
        </el-select>
        <el-select v-model="table.query.result" placeholder="执行结果" clearable style="width: 140px" @change="table.search()">
          <el-option label="成功" value="success" />
          <el-option label="部分成功" value="partial" />
          <el-option label="失败" value="fail" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column label="执行类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.exec_type === 'link' ? 'warning' : 'primary'">{{ row.exec_type_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="场景/规则" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.scene_name || row.rule_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="trigger_source" label="触发来源" width="120" />
        <el-table-column prop="total_count" label="动作总数" width="90" />
        <el-table-column prop="success_count" label="成功" width="80" />
        <el-table-column prop="fail_count" label="失败" width="80" />
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="resultTag(row.result)">{{ row.result_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.exec_time) }}</template>
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
