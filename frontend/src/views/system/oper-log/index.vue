<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listLoginLogs, listOperLogs, type LoginLog, type OperLog } from '@/api/system'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const activeTab = ref('oper')

const operTable = useTable<OperLog>(listOperLogs, { keyword: '', module: undefined, status: undefined })
const loginTable = useTable<LoginLog>(listLoginLogs, { keyword: '', status: undefined })

onMounted(() => {
  operTable.load()
  loginTable.load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>日志管理</h2></div>
      <el-tabs v-model="activeTab">
        <!-- 操作日志 -->
        <el-tab-pane label="操作日志" name="oper">
          <div class="filter-bar">
            <el-input
              v-model="operTable.query.keyword"
              placeholder="用户名 / 请求地址"
              clearable
              style="width: 220px"
              @keyup.enter="operTable.search()"
            />
            <el-select v-model="operTable.query.module" placeholder="全部模块" clearable style="width: 150px" @change="operTable.search()">
              <el-option label="基础配置" value="基础配置" />
              <el-option label="系统管理" value="系统管理" />
            </el-select>
            <el-select v-model="operTable.query.status" placeholder="全部状态" clearable style="width: 140px" @change="operTable.search()">
              <el-option label="成功" :value="1" />
              <el-option label="失败" :value="0" />
            </el-select>
            <el-button type="primary" @click="operTable.search()">查询</el-button>
            <el-button @click="operTable.reset()">重置</el-button>
          </div>

          <el-table v-loading="operTable.loading" :data="operTable.list" border>
            <el-table-column prop="username" label="操作人" width="120" />
            <el-table-column prop="module" label="模块" width="110" />
            <el-table-column prop="action" label="操作" width="90" />
            <el-table-column prop="method" label="方法" width="90" />
            <el-table-column prop="request_url" label="请求地址" min-width="200" show-overflow-tooltip />
            <el-table-column prop="ip" label="IP" width="140" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                  {{ row.status === 1 ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cost_ms" label="耗时(ms)" width="100" />
            <el-table-column label="操作时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.oper_time) }}</template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="table-pagination"
            :current-page="operTable.query.page"
            :page-size="operTable.query.page_size"
            :total="operTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="operTable.changePage"
            @size-change="operTable.changeSize"
          />
        </el-tab-pane>

        <!-- 登录日志 -->
        <el-tab-pane label="登录日志" name="login">
          <div class="filter-bar">
            <el-input
              v-model="loginTable.query.keyword"
              placeholder="用户名"
              clearable
              style="width: 220px"
              @keyup.enter="loginTable.search()"
            />
            <el-select v-model="loginTable.query.status" placeholder="全部状态" clearable style="width: 140px" @change="loginTable.search()">
              <el-option label="成功" :value="1" />
              <el-option label="失败" :value="0" />
            </el-select>
            <el-button type="primary" @click="loginTable.search()">查询</el-button>
            <el-button @click="loginTable.reset()">重置</el-button>
          </div>

          <el-table v-loading="loginTable.loading" :data="loginTable.list" border>
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="ip" label="IP" width="150" />
            <el-table-column prop="browser" label="浏览器" min-width="140" />
            <el-table-column prop="os" label="操作系统" min-width="140" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                  {{ row.status === 1 ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="msg" label="说明" min-width="150" show-overflow-tooltip />
            <el-table-column label="登录时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.login_time) }}</template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="table-pagination"
            :current-page="loginTable.query.page"
            :page-size="loginTable.query.page_size"
            :total="loginTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loginTable.changePage"
            @size-change="loginTable.changeSize"
          />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
