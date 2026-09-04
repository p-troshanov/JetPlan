<!-- frontend/src/components/tasks/TaskSearch.vue -->
<!-- Предоставляет общий поиск по загруженным задачам для списка и канбана. -->
<script setup lang="ts">
import { computed } from 'vue'
import { useTasksStore } from '@/stores/tasks'

defineProps<{
  resultCount: number
}>()

const store = useTasksStore()
const isSearchActive = computed(() => store.filters.searchQuery.trim().length > 0)
</script>

<template>
  <div class="task-search" role="search">
    <svg class="task-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8"></circle>
      <path d="m21 21-4.35-4.35"></path>
    </svg>
    <input
      v-model="store.filters.searchQuery"
      type="search"
      class="task-search-input"
      placeholder="Поиск по задачам"
      aria-label="Поиск по задачам"
      autocomplete="off"
      spellcheck="false"
      @keydown.esc="store.filters.searchQuery = ''"
    />
    <span
      v-if="isSearchActive"
      class="task-search-count"
      :aria-label="`Найдено задач: ${resultCount}`"
      aria-live="polite"
    >
      {{ resultCount }}
    </span>
    <button
      v-if="isSearchActive"
      type="button"
      class="task-search-clear"
      aria-label="Очистить поиск"
      title="Очистить поиск"
      @click="store.filters.searchQuery = ''"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <path d="M18 6 6 18"></path>
        <path d="m6 6 12 12"></path>
      </svg>
    </button>
  </div>
</template>
