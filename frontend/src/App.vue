// frontend/src/App.vue
// Предоставляет корневой адаптивный контейнер для всех маршрутов приложения.
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
  min-width: 0;
  min-height: 100dvh;
}
</style>
