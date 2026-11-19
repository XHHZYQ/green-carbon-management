<script setup lang="ts">
import TopologyEditor from '../components/TopologyEditor.vue'
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>区域平面图</h2></div>
      <TopologyEditor topo-type="plan" variant="floor" title="平面图" />
    </div>
  </div>
</template>
