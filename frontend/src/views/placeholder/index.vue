<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="page-container">
    <div class="page-card placeholder">
      <el-icon class="placeholder-icon"><Tools /></el-icon>
      <h2>{{ route.meta.title || '功能页面' }}</h2>
      <p>该功能将在后续开发批次中实现</p>
      <el-button type="primary" plain @click="$router.push('/dashboard')">返回驾驶舱</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 152px);
  gap: 12px;

  .placeholder-icon {
    font-size: 56px;
    color: $primary-color;
    opacity: 0.7;
  }

  h2 {
    margin: 0;
    color: $text-primary;
  }

  p {
    margin: 0 0 8px;
    color: $text-secondary;
  }
}
</style>
