<script setup lang="ts">
import { ref } from 'vue'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { accessApi, type ImportResult } from '@/api/device'

const rawFile = ref<File>()
const importing = ref(false)
const result = ref<ImportResult>()
const fileName = ref('')

function onFileChange(file: UploadFile) {
  rawFile.value = file.raw
  fileName.value = file.name
}

async function downloadTemplate() {
  const blob = await accessApi.importTemplate()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '设备导入模板.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

async function doImport() {
  if (!rawFile.value) return ElMessage.warning('请先选择导入文件')
  importing.value = true
  try {
    const form = new FormData()
    form.append('file', rawFile.value)
    result.value = await accessApi.importDevices(form)
    ElMessage.success(`导入完成：成功 ${result.value.success} 条，失败 ${result.value.failed} 条`)
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>批量导入</h2></div>

      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
        <template #title>
          支持 .xlsx / .csv 文件，列顺序：设备编号、设备名称、设备类型编码、所属区域、安装位置、通信协议编码。
          设备类型编码与通信协议编码需为系统已存在的编码。
        </template>
      </el-alert>

      <div class="toolbar">
        <el-button @click="downloadTemplate">下载导入模板</el-button>
      </div>

      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="false"
        accept=".xlsx,.csv"
        :on-change="onFileChange"
      >
        <div class="upload-inner">
          <div class="upload-text">将文件拖到此处，或点击选择</div>
          <div class="upload-tip">{{ fileName || '未选择文件' }}</div>
        </div>
      </el-upload>

      <div class="toolbar" style="margin-top: 16px">
        <el-button type="primary" :loading="importing" @click="doImport">开始导入</el-button>
        <el-button @click="rawFile = undefined; fileName = ''; result = undefined">清空</el-button>
      </div>

      <div v-if="result" style="margin-top: 16px">
        <el-alert
          :type="result.failed === 0 ? 'success' : 'warning'"
          :closable="false"
          show-icon
          :title="`成功 ${result.success} 条，失败 ${result.failed} 条`"
        />
        <el-table :data="result.messages.map((m, i) => ({ no: i + 1, msg: m }))" border size="small" style="margin-top: 12px">
          <el-table-column prop="no" label="#" width="60" />
          <el-table-column prop="msg" label="导入明细" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  gap: 8px;
}
.upload-inner {
  padding: 30px 0;
}
.upload-text {
  color: var(--el-text-color-primary);
}
.upload-tip {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 8px;
}
</style>
