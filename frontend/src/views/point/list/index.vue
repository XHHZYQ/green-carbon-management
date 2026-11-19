<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deviceApi, type DeviceItem } from '@/api/device'
import { pointApi, pointTemplateApi, type PointItem, type PointTemplateItem } from '@/api/point'
import { deviceTypeApi, type DeviceType } from '@/api/config'
import { useTable } from '@/composables/useTable'

const activeTab = ref('points')
const devices = ref<DeviceItem[]>([])
const types = ref<DeviceType[]>([])
const dataTypes = ['float', 'int', 'bool', 'string']

const pointTable = useTable<PointItem>(pointApi.list, { keyword: '', device_id: undefined })
const tplTable = useTable<PointTemplateItem>(pointTemplateApi.list, { keyword: '' })

onMounted(async () => {
  pointTable.load()
  tplTable.load()
  const [d, t] = await Promise.all([deviceApi.list({ page: 1, page_size: 200 }), deviceTypeApi.list({ page: 1, page_size: 100 })])
  devices.value = d.items
  types.value = t.items
})

const pointDialog = ref(false)
const pointEditingId = ref<number>()
const pointForm = reactive<Record<string, any>>({})

function openPointCreate() {
  pointEditingId.value = undefined
  Object.assign(pointForm, { device_id: undefined, point_code: '', point_name: '', data_type: 'float', unit: '', range_min: undefined, range_max: undefined, point_type: 'collect', sort_no: 0, status: 1 })
  pointDialog.value = true
}
function openPointEdit(row: PointItem) {
  pointEditingId.value = row.id
  Object.assign(pointForm, row)
  pointDialog.value = true
}
async function submitPoint() {
  if (!pointForm.device_id || !pointForm.point_code || !pointForm.point_name) return ElMessage.warning('请填写设备、测点编码与名称')
  if (pointEditingId.value) await pointApi.update(pointEditingId.value, { ...pointForm })
  else await pointApi.create({ ...pointForm })
  ElMessage.success('保存成功')
  pointDialog.value = false
  pointTable.load()
}
async function removePoint(row: PointItem) {
  await ElMessageBox.confirm(`确定删除测点「${row.point_name}」？`, '提示', { type: 'warning' })
  await pointApi.remove(row.id as number)
  ElMessage.success('删除成功')
  pointTable.load()
}

const tplDialog = ref(false)
const tplEditingId = ref<number>()
const tplForm = reactive<Record<string, any>>({})

function openTplCreate() {
  tplEditingId.value = undefined
  Object.assign(tplForm, { template_code: '', template_name: '', device_type_id: undefined, description: '', status: 1 })
  tplDialog.value = true
}
function openTplEdit(row: PointTemplateItem) {
  tplEditingId.value = row.id
  Object.assign(tplForm, row)
  tplDialog.value = true
}
async function submitTpl() {
  if (!tplForm.template_code || !tplForm.template_name) return ElMessage.warning('请填写模板编码与名称')
  if (tplEditingId.value) await pointTemplateApi.update(tplEditingId.value, { ...tplForm })
  else await pointTemplateApi.create({ ...tplForm })
  ElMessage.success('保存成功')
  tplDialog.value = false
  tplTable.load()
}
async function removeTpl(row: PointTemplateItem) {
  await ElMessageBox.confirm(`确定删除模板「${row.template_name}」？`, '提示', { type: 'warning' })
  await pointTemplateApi.remove(row.id as number)
  ElMessage.success('删除成功')
  tplTable.load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>测点管理</h2></div>
      <el-tabs v-model="activeTab">
        <!-- 测点列表 -->
        <el-tab-pane label="测点列表" name="points">
          <div class="filter-bar">
            <el-input v-model="pointTable.query.keyword" placeholder="测点编码 / 名称" clearable style="width: 200px" @keyup.enter="pointTable.search()" />
            <el-select v-model="pointTable.query.device_id" placeholder="所属设备" clearable filterable style="width: 220px" @change="pointTable.search()">
              <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
            </el-select>
            <el-button type="primary" @click="pointTable.search()">查询</el-button>
            <el-button @click="pointTable.reset()">重置</el-button>
            <el-button type="primary" style="margin-left: auto" @click="openPointCreate">新增测点</el-button>
          </div>
          <el-table v-loading="pointTable.loading" :data="pointTable.list" border>
            <el-table-column prop="device_name" label="所属设备" min-width="160" show-overflow-tooltip />
            <el-table-column prop="point_code" label="测点编码" width="150" />
            <el-table-column prop="point_name" label="测点名称" min-width="150" />
            <el-table-column prop="data_type" label="数据类型" width="100" />
            <el-table-column prop="unit" label="单位" width="90" />
            <el-table-column label="量程" width="150">
              <template #default="{ row }">{{ row.range_min ?? '-' }} ~ {{ row.range_max ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openPointEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="removePoint(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            class="table-pagination"
            :current-page="pointTable.query.page"
            :page-size="pointTable.query.page_size"
            :total="pointTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="pointTable.changePage"
            @size-change="pointTable.changeSize"
          />
        </el-tab-pane>

        <!-- 测点模板 -->
        <el-tab-pane label="测点模板" name="templates">
          <div class="filter-bar">
            <el-input v-model="tplTable.query.keyword" placeholder="模板编码 / 名称" clearable style="width: 200px" @keyup.enter="tplTable.search()" />
            <el-button type="primary" @click="tplTable.search()">查询</el-button>
            <el-button @click="tplTable.reset()">重置</el-button>
            <el-button type="primary" style="margin-left: auto" @click="openTplCreate">新增模板</el-button>
          </div>
          <el-table v-loading="tplTable.loading" :data="tplTable.list" border>
            <el-table-column prop="template_code" label="模板编码" width="200" />
            <el-table-column prop="template_name" label="模板名称" min-width="200" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openTplEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="removeTpl(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            class="table-pagination"
            :current-page="tplTable.query.page"
            :page-size="tplTable.query.page_size"
            :total="tplTable.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="tplTable.changePage"
            @size-change="tplTable.changeSize"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="pointDialog" :title="pointEditingId ? '编辑测点' : '新增测点'" width="520px">
      <el-form :model="pointForm" label-width="90px">
        <el-form-item label="所属设备" required>
          <el-select v-model="pointForm.device_id" filterable style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.device_name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测点编码" required><el-input v-model="pointForm.point_code" /></el-form-item>
        <el-form-item label="测点名称" required><el-input v-model="pointForm.point_name" /></el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="pointForm.data_type" style="width: 100%">
            <el-option v-for="t in dataTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位"><el-input v-model="pointForm.unit" /></el-form-item>
        <el-form-item label="量程下限"><el-input-number v-model="pointForm.range_min" :controls="false" style="width: 100%" /></el-form-item>
        <el-form-item label="量程上限"><el-input-number v-model="pointForm.range_max" :controls="false" style="width: 100%" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="pointForm.sort_no" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="pointForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pointDialog = false">取消</el-button>
        <el-button type="primary" @click="submitPoint">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tplDialog" :title="tplEditingId ? '编辑模板' : '新增模板'" width="520px">
      <el-form :model="tplForm" label-width="90px">
        <el-form-item label="模板编码" required><el-input v-model="tplForm.template_code" :disabled="!!tplEditingId" /></el-form-item>
        <el-form-item label="模板名称" required><el-input v-model="tplForm.template_name" /></el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="tplForm.device_type_id" clearable style="width: 100%">
            <el-option v-for="t in types" :key="t.id" :label="t.type_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="tplForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="tplForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tplDialog = false">取消</el-button>
        <el-button type="primary" @click="submitTpl">保存</el-button>
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
