<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="error-page">
    <div class="error-code">404</div>
    <p class="error-text">抱歉，您访问的页面不存在</p>
    <el-button type="primary" @click="router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.error-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: $page-bg;
}

.error-code {
  font-size: 96px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(135deg, $primary-color, #40a9ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.error-text {
  margin: 0;
  color: $text-secondary;
}
</style>
