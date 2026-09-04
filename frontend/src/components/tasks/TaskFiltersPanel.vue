<!-- frontend/src/components/tasks/TaskFiltersPanel.vue -->
<!-- Отображает единый набор фильтров задач во всех представлениях рабочего пространства. -->
<script setup lang="ts">
import { useTasksStore } from '@/stores/tasks'
import { TASK_PRIORITIES } from '@/utils/taskPlanning'

withDefaults(defineProps<{
  idPrefix?: string
  manualSort?: boolean
  hideFutureIgnored?: boolean
}>(), {
  idPrefix: 'tasks',
  manualSort: false,
  hideFutureIgnored: false,
})

defineEmits<{
  resetManualSort: []
}>()

const store = useTasksStore()
</script>

<template>
  <div class="filters-grid">
    <div class="filter-group">
      <label :for="`${idPrefix}-status`">Статус</label>
      <select :id="`${idPrefix}-status`" v-model="store.filters.selectedStatus" class="form-control">
        <option value="pending">Активные</option>
        <option value="completed">Выполненные</option>
        <option value="all">Все</option>
      </select>
    </div>

    <div class="filter-group">
      <label :for="`${idPrefix}-date`">Дата</label>
      <input :id="`${idPrefix}-date`" v-model="store.filters.selectedDate" type="date" class="form-control" />
    </div>

    <div class="filter-group">
      <label :for="`${idPrefix}-category`">Категория</label>
      <select :id="`${idPrefix}-category`" v-model="store.filters.selectedCategoryId" class="form-control">
        <option value="">Все категории</option>
        <option v-for="category in store.categories" :key="category.id" :value="category.id">
          {{ category.name }}
        </option>
      </select>
    </div>

    <div class="filter-group">
      <label :for="`${idPrefix}-priority`">Приоритет</label>
      <select :id="`${idPrefix}-priority`" v-model="store.filters.selectedPriority" class="form-control">
        <option value="">Любой</option>
        <option v-for="priority in TASK_PRIORITIES" :key="priority.value" :value="priority.value">
          {{ priority.label }}
        </option>
      </select>
    </div>

    <div class="filter-group">
      <span class="filter-label">Отображение</span>
      <label class="checkbox-label">
        <input v-model="store.filters.hideFutureTasks" type="checkbox" />
        Скрыть будущие
      </label>
      <small v-if="hideFutureIgnored" class="filter-note">
        В режиме «Дата» ближайшие семь дней остаются видимыми.
      </small>
      <label class="checkbox-label">
        <input v-model="store.filters.showOnlyOverdue" type="checkbox" />
        Только просроченные
      </label>
    </div>

    <div v-if="manualSort" class="filter-group">
      <span class="filter-label">Сортировка</span>
      <button class="btn btn-secondary btn-small" type="button" @click="$emit('resetManualSort')">
        Сбросить ручную
      </button>
    </div>
  </div>
</template>
