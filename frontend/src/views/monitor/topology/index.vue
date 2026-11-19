<script setup lang="ts">
import TopologyEditor from '../components/TopologyEditor.vue'
</script>

<template>
  <div class="page-container">
    <div class="page-card">
      <div class="page-title"><h2>设备组态图</h2></div>
      <TopologyEditor topo-type="topology" variant="grid" title="组态图" />
    </div>
  </div>
</template>
