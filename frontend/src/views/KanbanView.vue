<!-- frontend/src/views/KanbanView.vue -->
<!-- Собирает защищённую страницу канбана, общие фильтры и три режима группировки задач. -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import WorkspaceHeader from '@/components/WorkspaceHeader.vue'
import KanbanBoard from '@/components/tasks/KanbanBoard.vue'
import TaskFiltersPanel from '@/components/tasks/TaskFiltersPanel.vue'
import TaskModal from '@/components/tasks/TaskModal.vue'
import TaskSearch from '@/components/tasks/TaskSearch.vue'
import { useTasksStore } from '@/stores/tasks'
import { filterTasks, type KanbanMode } from '@/utils/taskPlanning'
import type { Task } from '@/types'
import '@/assets/tasks.css'
import '@/assets/kanban.css'

const store = useTasksStore()
const mode = ref<KanbanMode>('priority')
const showFilters = ref(false)
const showTaskModal = ref(false)
const editingTask = ref<Task | null>(null)
const boardError = ref<string | null>(null)
const referenceDate = ref(new Date())
let pollInterval: ReturnType<typeof setInterval> | undefined

const modes: Array<{ value: KanbanMode; label: string }> = [
  { value: 'priority', label: 'Приоритет' },
  { value: 'category', label: 'Категория' },
  { value: 'date', label: 'Дата' },
]

const modeDescription = computed(() => {
  if (mode.value === 'priority') return 'Переносите задачи между высоким, средним и низким приоритетом.'
  if (mode.value === 'category') return 'Распределяйте задачи по доступным категориям или оставляйте во входящих.'
  return 'Планируйте ближайшие семь локальных дней. Время задачи сохраняется, а задача без срока получает 09:00.'
})

const visibleTaskCount = computed(() => filterTasks(store.tasks, store.filters, {
  ignoreHideFuture: mode.value === 'date',
}).length)

const syncTasks = () => {
  referenceDate.value = new Date()
  if (!showTaskModal.value) {
    void store.fetchCategories()
    void store.fetchTasks(true)
  }
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') syncTasks()
}

onMounted(async () => {
  await Promise.all([store.fetchCategories(), store.fetchTasks()])
  window.addEventListener('focus', syncTasks)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  pollInterval = setInterval(syncTasks, 10000)
})

onUnmounted(() => {
  window.removeEventListener('focus', syncTasks)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (pollInterval) clearInterval(pollInterval)
})

const openCreateModal = () => {
  editingTask.value = null
  showTaskModal.value = true
}

const openEditModal = (task: Task) => {
  editingTask.value = task
  showTaskModal.value = true
}

const closeTaskModal = () => {
  showTaskModal.value = false
  editingTask.value = null
}
</script>

<template>
  <main class="kanban-view">
    <WorkspaceHeader />

    <section class="kanban-shell" aria-labelledby="kanban-title">
      <div class="kanban-title-row">
        <div>
          <p class="kanban-eyebrow">Представление задач</p>
          <h1 id="kanban-title">Канбан</h1>
          <p class="kanban-description">{{ modeDescription }}</p>
        </div>
        <button class="btn btn-primary kanban-create" type="button" @click="openCreateModal">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 5v14M5 12h14"></path>
          </svg>
          Создать задачу
        </button>
      </div>

      <div class="kanban-toolbar">
        <div class="kanban-mode-switch" role="tablist" aria-label="Группировка канбана">
          <button
            v-for="item in modes"
            :key="item.value"
            :id="`kanban-mode-${item.value}`"
            type="button"
            role="tab"
            aria-controls="kanban-board"
            :aria-selected="mode === item.value"
            :class="{ active: mode === item.value }"
            @click="mode = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <TaskSearch :result-count="visibleTaskCount" />

        <button class="btn btn-secondary kanban-filter-toggle" type="button" @click="showFilters = !showFilters">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M4 5h16M7 12h10M10 19h4"></path>
          </svg>
          {{ showFilters ? 'Скрыть фильтры' : 'Фильтры' }}
        </button>
      </div>

      <div v-if="showFilters" class="filters-panel kanban-filters">
        <TaskFiltersPanel id-prefix="kanban" :hide-future-ignored="mode === 'date'" />
      </div>

      <div v-if="boardError" class="kanban-error" role="alert">
        <span>{{ boardError }}. Предыдущее положение задачи восстановлено.</span>
        <button type="button" aria-label="Закрыть сообщение" @click="boardError = null">×</button>
      </div>

      <div
        id="kanban-board"
        role="tabpanel"
        :aria-labelledby="`kanban-mode-${mode}`"
      >
        <div v-if="store.isLoading" class="kanban-loading" aria-live="polite">Загрузка задач…</div>
        <KanbanBoard
          v-else
          :mode="mode"
          :reference-date="referenceDate"
          @edit="openEditModal"
          @error="boardError = $event"
        />
      </div>
    </section>

    <TaskModal
      v-if="showTaskModal"
      :task-to-edit="editingTask"
      @close="closeTaskModal"
      @saved="closeTaskModal"
    />
  </main>
</template>
