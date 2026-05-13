// frontend/src/App.vue
<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app-wrapper">
    <RouterView />
  </div>
</template>

<style scoped>
.app-wrapper {
  width: 100%;
  min-height: 100vh;
  padding: 2rem;
}

@media (max-width: 1024px) {
  .app-wrapper {
    padding: 1rem;
  }
}
</style>
