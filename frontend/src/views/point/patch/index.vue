<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { deviceApi, type DeviceItem } from '@/api/device'
import { dataApi, pointApi, type DeviceDataItem, type PointItem } from '@/api/point'
import { useTable } from '@/composables/useTable'
import { formatDateTime } from '@/utils/format'

const devices = ref<DeviceItem[]>([])
const points = ref<PointItem[]>([])
const timeRange = ref<[string, string]>()

const qualityMap: Record<string, string> = { normal: '正常', abnormal: '异常', missing: '缺失', patched: '已补录' }
const qualityTag: Record<string, string> = { normal: 'success', abnormal: 'danger', missing: 'info', patched: 'warning' }

const table = useTable<DeviceDataItem>(dataApi.list, {
  device_id: undefined,
  point_id: undefined,
  data_quality: undefined,
  start_time: undefined,
  end_time: undefined,
})

const patchVisible = ref(false)
const patchForm = reactive({ data_id: 0, patch_value: '' as number | string, reason: '' })
const qualityVisible = ref(false)
const qualityForm = reactive({ data_id: 0, data_quality: 'normal' })

onMounted(async () => {
  const d = await deviceApi.list({ page: 1, page_size: 200 })
  devices.value = d.items
  table.load()
})

watch(() => table.query.device_id, async (id) => {
  table.query.point_id = undefined
  points.value = id ? (await pointApi.list({ device_id: id, page: 1, page_size: 200 })).items : []
})

function load() {
  if (timeRange.value) {
    table.query.start_time = timeRange.value[0]
    table.query.end_time = timeRange.value[1]
  }
  table.search()
}

function reset() {
  timeRange.value = undefined
  table.reset()
}

function openPatch(row: DeviceDataItem) {
  patchForm.data_id = row.id
  patchForm.patch_value = row.collect_value as number
  patchForm.reason = ''
  patchVisible.value = true
}

async function submitPatch() {
  if (patchForm.patch_value === '' || patchForm.patch_value === null) {
    ElMessage.warning('请输入补录值')
    return
  }
  await dataApi.patch({ data_id: patchForm.data_id, patch_value: patchForm.patch_value, reason: patchForm.reason })
  ElMessage.success('补录成功')
  patchVisible.value = false
  table.load()
}

function openQuality(row: DeviceDataItem) {
  qualityForm.data_id = row.id
  qualityForm.data_quality = row.data_quality
  qualityVisible.value = true
}

async function submitQuality() {
  await dataApi.setQuality(qualityForm.data_id, qualityForm.data_quality)
  ElMessage.success('标记成功')
  qualityVisible.value = false
  table.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>数据补录</h2></div>

      <div class="filter-bar">
        <el-select v-model="table.query.device_id" placeholder="选择设备" clearable filterable style="width: 200px">
          <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
        </el-select>
        <el-select v-model="table.query.point_id" placeholder="选择测点" clearable filterable style="width: 180px">
          <el-option v-for="p in points" :key="p.id" :label="p.point_name" :value="p.id" />
        </el-select>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 360px"
        />
        <el-select v-model="table.query.data_quality" placeholder="数据质量" clearable style="width: 130px">
          <el-option label="正常" value="normal" />
          <el-option label="异常" value="abnormal" />
          <el-option label="缺失" value="missing" />
          <el-option label="已补录" value="patched" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column label="采集时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.collect_time) }}</template>
        </el-table-column>
        <el-table-column prop="collect_value" label="采集值" width="140" />
        <el-table-column prop="unit" label="单位" width="100" />
        <el-table-column label="数据质量" width="110">
          <template #default="{ row }">
            <el-tag :type="qualityTag[row.data_quality]" size="small">
              {{ qualityMap[row.data_quality] || row.data_quality }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPatch(row)">补录</el-button>
            <el-button link type="warning" @click="openQuality(row)">质量标记</el-button>
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

    <el-dialog v-model="patchVisible" title="数据补录" width="420px">
      <el-form label-width="90px">
        <el-form-item label="补录值" required>
          <el-input v-model="patchForm.patch_value" placeholder="请输入补录值" />
        </el-form-item>
        <el-form-item label="补录原因">
          <el-input v-model="patchForm.reason" type="textarea" :rows="3" placeholder="请输入补录原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="patchVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPatch">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qualityVisible" title="数据质量标记" width="420px">
      <el-form label-width="90px">
        <el-form-item label="数据质量">
          <el-select v-model="qualityForm.data_quality" style="width: 100%">
            <el-option label="正常" value="normal" />
            <el-option label="异常" value="abnormal" />
            <el-option label="缺失" value="missing" />
            <el-option label="已补录" value="patched" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="qualityVisible = false">取消</el-button>
        <el-button type="primary" @click="submitQuality">确定</el-button>
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
