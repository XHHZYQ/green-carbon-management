<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { accessApi, areaApi, deviceApi, type AreaNode } from '@/api/device'
import { type DeviceType, type Protocol, type ProtocolParam } from '@/api/config'
import { pointTemplateApi, type PointTemplateItem } from '@/api/point'

const router = useRouter()
const active = ref(0)

const types = ref<DeviceType[]>([])
const protocols = ref<(Protocol & { is_default?: boolean })[]>([])
const params = ref<ProtocolParam[]>([])
const areaTree = ref<AreaNode[]>([])
const templates = ref<PointTemplateItem[]>([])
const treeProps = { label: 'area_name', value: 'id', children: 'children' }

const selType = ref<DeviceType>()
const selProtocol = ref<Protocol>()
const paramValues = reactive<Record<string, string>>({})
const testResult = ref<{ success: boolean; message: string; cost_ms: number }>()

const form = reactive<Record<string, any>>({
  device_code: '',
  device_name: '',
  area_id: undefined,
  install_location: '',
  remark: '',
  point_template_id: undefined,
  enable_online: true,
})

const canNext = computed(() => {
  if (active.value === 0) return !!selType.value
  if (active.value === 1) return !!selProtocol.value
  if (active.value === 2) return !!form.device_code && !!form.device_name
  return true
})

onMounted(async () => {
  const [t, a, tp] = await Promise.all([accessApi.wizardTypes(), areaApi.tree(), pointTemplateApi.list({ page: 1, page_size: 100 })])
  types.value = t
  areaTree.value = a
  templates.value = tp.items
})

async function chooseType(t: DeviceType) {
  selType.value = t
  selProtocol.value = undefined
  await loadProtocols()
  active.value = 1
}

async function loadProtocols() {
  protocols.value = await accessApi.wizardProtocols(selType.value?.id)
  const def = protocols.value.find((p) => p.is_default)
  if (def) selProtocol.value = def
}

async function chooseProtocol(p: Protocol) {
  selProtocol.value = p
  await loadParams()
  active.value = 2
}

async function loadParams() {
  params.value = await accessApi.wizardParams(selProtocol.value?.id)
  for (const k of Object.keys(paramValues)) delete paramValues[k]
  for (const p of params.value) paramValues[p.param_key] = p.default_value ?? ''
}

async function doTest() {
  testResult.value = await accessApi.testConnection({
    protocol_id: selProtocol.value?.id,
    device_type_id: selType.value?.id,
    params: { ...paramValues },
  })
}

async function submit() {
  if (form.enable_online && !testResult.value?.success) return ElMessage.warning('请先通过测试连接，未通过不得上线')
  await deviceApi.create({
    device_code: form.device_code,
    device_name: form.device_name,
    device_type_id: selType.value?.id,
    area_id: form.area_id,
    protocol_id: selProtocol.value?.id,
    install_location: form.install_location,
    remark: form.remark,
    point_template_id: form.point_template_id,
    enable_online: form.enable_online,
    params: { ...paramValues },
  })
  active.value = 3
}

function restart() {
  active.value = 0
  selType.value = undefined
  selProtocol.value = undefined
  testResult.value = undefined
  Object.assign(form, { device_code: '', device_name: '', area_id: undefined, install_location: '', remark: '', point_template_id: undefined, enable_online: true })
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备接入向导</h2></div>

      <el-steps :active="active" finish-status="success" align-center style="margin-bottom: 24px">
        <el-step title="选择设备类型" />
        <el-step title="选择通信协议" />
        <el-step title="填写连接参数" />
        <el-step title="接入完成" />
      </el-steps>

      <!-- 步骤1：设备类型 -->
      <div v-if="active === 0">
        <div class="type-grid">
          <div v-for="t in types" :key="t.id" class="type-card" :class="{ active: selType?.id === t.id }" @click="chooseType(t)">
            <div class="type-name">{{ t.type_name }}</div>
            <div class="type-code">{{ t.type_code }}</div>
          </div>
        </div>
      </div>

      <!-- 步骤2：协议 -->
      <div v-else-if="active === 1">
        <el-radio-group v-model="selProtocol" class="protocol-list">
          <el-radio v-for="p in protocols" :key="p.id" :value="p" border class="protocol-item">
            {{ p.protocol_name }}
            <el-tag v-if="p.is_default" type="success" size="small" style="margin-left: 8px">推荐</el-tag>
          </el-radio>
        </el-radio-group>
        <div class="step-actions">
          <el-button @click="active = 0">上一步</el-button>
          <el-button type="primary" :disabled="!selProtocol" @click="chooseProtocol(selProtocol as Protocol)">下一步</el-button>
        </div>
      </div>

      <!-- 步骤3：参数 -->
      <div v-else-if="active === 2">
        <el-form :model="form" label-width="110px" style="max-width: 620px">
          <el-divider content-position="left">设备信息</el-divider>
          <el-form-item label="设备编号" required><el-input v-model="form.device_code" placeholder="如 GC-METER_E-001" /></el-form-item>
          <el-form-item label="设备名称" required><el-input v-model="form.device_name" /></el-form-item>
          <el-form-item label="所属区域">
            <el-tree-select v-model="form.area_id" :data="areaTree" :props="treeProps" check-strictly clearable style="width: 100%" />
          </el-form-item>
          <el-form-item label="安装位置"><el-input v-model="form.install_location" /></el-form-item>
          <el-form-item label="测点模板">
            <el-select v-model="form.point_template_id" clearable placeholder="可选，按模板生成测点" style="width: 100%">
              <el-option v-for="t in templates" :key="t.id" :label="t.template_name" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>

          <el-divider content-position="left">连接参数（{{ selProtocol?.protocol_name }}）</el-divider>
          <el-form-item v-for="p in params" :key="p.id" :label="p.param_label" :required="p.required">
            <el-input v-model="paramValues[p.param_key]" :placeholder="p.default_value || ''" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="form.enable_online" active-text="接入后立即上线" />
          </el-form-item>
          <el-form-item label="测试连接">
            <el-button @click="doTest">测试连接</el-button>
            <span v-if="testResult" :class="testResult.success ? 'test-ok' : 'test-fail'">
              {{ testResult.message }}（耗时 {{ testResult.cost_ms }}ms）
            </span>
          </el-form-item>
        </el-form>
        <div class="step-actions">
          <el-button @click="active = 1">上一步</el-button>
          <el-button type="primary" :disabled="!canNext" @click="submit">保存并接入</el-button>
        </div>
      </div>

      <!-- 步骤4：完成 -->
      <el-result v-else icon="success" title="设备接入成功" :sub-title="`设备「${form.device_name}」已保存${form.enable_online ? '并上线' : ''}`">
        <template #extra>
          <el-button type="primary" @click="router.push('/device/list')">查看设备台账</el-button>
          <el-button @click="restart">继续接入</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<style scoped lang="scss">
.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.type-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}
.type-card:hover,
.type-card.active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-7);
}
.type-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.type-code {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
}
.protocol-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 420px;
}
.protocol-item {
  width: 100%;
  margin-right: 0;
}
.step-actions {
  margin-top: 20px;
}
.test-ok {
  color: var(--el-color-success);
  margin-left: 12px;
}
.test-fail {
  color: var(--el-color-danger);
  margin-left: 12px;
}
</style>
