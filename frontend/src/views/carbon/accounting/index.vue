<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { carbonApi, type CarbonEmissionItem } from '@/api/carbon'
import { areaApi, type AreaNode } from '@/api/device'
import { useTable } from '@/composables/useTable'
import { formatDateTime, formatNumber } from '@/utils/format'

const table = useTable<CarbonEmissionItem>(carbonApi.emissions, { page_size: 10, period_type: undefined, area_id: undefined })
const areaOptions = ref<AreaNode[]>([])
const calcForm = ref({ period_type: 'month', period_value: '' })
const calcLoading = ref(false)

const periodTypeOptions = [
  { label: '按月', value: 'month' },
  { label: '按年', value: 'year' },
]

function flattenAreas(nodes: AreaNode[], acc: AreaNode[] = []): AreaNode[] {
  nodes.forEach((n) => {
    acc.push(n)
    if (n.children?.length) flattenAreas(n.children, acc)
  })
  return acc
}

async function doCalc() {
  calcLoading.value = true
  try {
    const res = await carbonApi.calc({
      period_type: calcForm.value.period_type,
      period_value: calcForm.value.period_value || null,
    })
    ElMessage.success(`核算完成，共写入 ${res.inserted} 条排放记录`)
    await table.search()
  } finally {
    calcLoading.value = false
  }
}

onMounted(async () => {
  const tree = await areaApi.tree()
  areaOptions.value = flattenAreas(tree)
  await table.load()
})
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>碳排放核算</h2></div>
      <div class="filter-bar">
        <el-select v-model="calcForm.period_type" style="width: 120px">
          <el-option v-for="p in periodTypeOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-date-picker
          v-if="calcForm.period_type === 'month'"
          v-model="calcForm.period_value"
          type="month"
          value-format="YYYY-MM"
          placeholder="选择月份"
          style="width: 180px"
        />
        <el-input
          v-else
          v-model="calcForm.period_value"
          placeholder="如 2026"
          style="width: 180px"
        />
        <el-button type="primary" :loading="calcLoading" @click="doCalc">执行核算</el-button>
        <span class="tip">排放量 = 能耗量 × 碳因子，未选周期时默认核算最近 12 个月</span>
      </div>
    </div>

    <div class="page-card row-gap">
      <div class="page-title"><h2>碳排放明细</h2></div>
      <div class="filter-bar">
        <el-select v-model="table.query.period_type" placeholder="周期类型" clearable style="width: 140px" @change="table.search()">
          <el-option v-for="p in periodTypeOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-select v-model="table.query.area_id" placeholder="区域" clearable style="width: 180px" @change="table.search()">
          <el-option v-for="a in areaOptions" :key="a.id" :label="a.area_name" :value="a.id" />
        </el-select>
        <el-button type="primary" @click="table.search()">查询</el-button>
        <el-button @click="table.reset()">重置</el-button>
      </div>

      <el-table v-loading="table.loading" :data="table.list" border>
        <el-table-column prop="period_value" label="周期" width="110" />
        <el-table-column prop="scope" label="排放范围" width="100" />
        <el-table-column prop="energy_type_name" label="能源类型" width="110" />
        <el-table-column prop="area_name" label="区域" width="130" />
        <el-table-column label="能耗量" min-width="120">
          <template #default="{ row }">{{ formatNumber(row.energy_value, 2) }}</template>
        </el-table-column>
        <el-table-column prop="factor_name" label="碳因子" min-width="140" />
        <el-table-column label="排放量 (tCO2e)" min-width="140">
          <template #default="{ row }">{{ formatNumber(row.emission_value, 2) }}</template>
        </el-table-column>
        <el-table-column label="核算时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
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
.row-gap {
  margin-top: 16px;
}

.tip {
  font-size: 12px;
  color: #8a97a8;
  align-self: center;
}

.table-pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
