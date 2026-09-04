// frontend/src/components/tasks/TasksDashboard.vue
// Отображает список задач, фильтры и управляет фоновым обновлением данных.
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { useUserStore } from '@/stores/user'
import draggable from 'vuedraggable'
import type { Task } from '@/types'
import { TASK_PRIORITIES, filterTasks } from '@/utils/taskPlanning'
import { buildTaskDescriptionPreview } from '@/utils/taskDescription'
import '@/assets/tasks.css'

import TaskModal from './TaskModal.vue'
import CategoryModal from './CategoryModal.vue'
import TaskFiltersPanel from './TaskFiltersPanel.vue'
import TaskSearch from './TaskSearch.vue'

const store = useTasksStore()
const userStore = useUserStore()

// Модалки
const showTaskModal = ref(false)
const showCatModal = ref(false)
const editingTask = ref<Task | null>(null)

// Видимость блока фильтров
const showFilters = ref(false)

const normalizedSearchQuery = computed(() => store.filters.searchQuery.trim().toLocaleLowerCase('ru-RU'))
const isSearchActive = computed(() => normalizedSearchQuery.value.length > 0)

// Ручная сортировка действует только внутри списка; фильтры общие с канбаном.
const isManualSort = ref(false)

// Интервал фонового обновления
let pollInterval: ReturnType<typeof setInterval> | undefined

// Состояние развернутых текстов задач
const expandedTasks = ref<Set<number>>(new Set())

const toggleTaskText = (taskId: number) => {
  const newSet = new Set(expandedTasks.value)
  if (newSet.has(taskId)) {
    newSet.delete(taskId)
  } else {
    newSet.add(taskId)
  }
  expandedTasks.value = newSet
}

// Генерация стилей категории для темной темы
const getCategoryStyle = (str: string) => {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash) % 360
  
  return {
    color: `hsl(${hue}, 80%, 75%)`,
    backgroundColor: `hsla(${hue}, 80%, 75%, 0.1)`,
    borderColor: `hsla(${hue}, 80%, 75%, 0.3)`
  }
}

const syncOnFocus = () => {
  if (!showTaskModal.value && !showCatModal.value) {
    store.fetchTasks(true) // фоновая загрузка, чтобы UI не мигал
  }
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') syncOnFocus()
}

onMounted(async () => {
  await userStore.fetchProfile()
  await store.fetchCategories()
  await store.fetchTasks()
  window.addEventListener('keydown', handleGlobalKeydown)
  
  window.addEventListener('focus', syncOnFocus)
  document.addEventListener('visibilitychange', handleVisibilityChange)

  // Фоновый поллинг новых задач из Телеграма каждые 10 секунд
  pollInterval = setInterval(() => {
    // Не обновляем, если открыты модалки
    if (!showTaskModal.value && !showCatModal.value) {
      store.fetchTasks(true)
    }
  }, 10000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  window.removeEventListener('focus', syncOnFocus)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (pollInterval) clearInterval(pollInterval)
})

const handleGlobalKeydown = (e: KeyboardEvent) => {
  if (showTaskModal.value || showCatModal.value) return;
  
  const hotkey = userStore.profile?.task_hotkey || 'ctrl+q';
  const parts = hotkey.toLowerCase().split('+');
  const hasCtrl = parts.includes('ctrl') || parts.includes('cmd');
  const hasAlt = parts.includes('alt');
  const hasShift = parts.includes('shift');
  const key = parts[parts.length - 1];

  const codeKey = e.code.toLowerCase().replace('key', '').replace('digit', '');
  const isKeyMatch = e.key.toLowerCase() === key || codeKey === key;

  if (
    (e.ctrlKey || e.metaKey) === hasCtrl &&
    e.altKey === hasAlt &&
    e.shiftKey === hasShift &&
    isKeyMatch
  ) {
    e.preventDefault();
    openCreateModal();
  }
}

type TextSegment = {
  text: string
  isMatch: boolean
}

const getVisibleTaskDescription = (task: Task) => {
  if (isSearchActive.value || expandedTasks.value.has(task.id)) {
    return task.description
  }

  return buildTaskDescriptionPreview(task.description).text
}

const canToggleTaskDescription = (task: Task) => (
  !isSearchActive.value && buildTaskDescriptionPreview(task.description).isTruncated
)

const getHighlightedSegments = (text: string): TextSegment[] => {
  const query = store.filters.searchQuery.trim()
  if (!query) return [{ text, isMatch: false }]

  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const matcher = new RegExp(escapedQuery, 'giu')
  const segments: TextSegment[] = []
  let lastIndex = 0

  for (const match of text.matchAll(matcher)) {
    const matchIndex = match.index ?? 0
    if (matchIndex > lastIndex) {
      segments.push({ text: text.slice(lastIndex, matchIndex), isMatch: false })
    }
    segments.push({ text: match[0], isMatch: true })
    lastIndex = matchIndex + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), isMatch: false })
  }

  return segments.length > 0 ? segments : [{ text, isMatch: false }]
}

const filteredAndSortedTasks = computed(() => filterTasks(store.tasks, store.filters, {
  manualSort: isManualSort.value,
}))

// Двухстороннее связывание для vuedraggable
const draggableTasks = computed({
  get: () => filteredAndSortedTasks.value,
  set: async (newList) => {
    isManualSort.value = true
    const taskIds = newList.map(t => t.id)
    await store.reorderTasks(taskIds)
  }
})

const openCreateModal = () => {
  editingTask.value = null
  showTaskModal.value = true
}

const openEditModal = (task: Task) => {
  editingTask.value = task
  showTaskModal.value = true
}

const toggleStatus = async (task: Task) => {
  const newStatus = task.status === 'completed' ? 'pending' : 'completed'
  await store.updateTask(task.id, { status: newStatus })
}

const formatDate = (dateStr?: string | null) => {
  if (!dateStr) return 'Без даты'
  const date = new Date(dateStr)
  const now = new Date()
  const dateDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const nowDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((dateDay.getTime() - nowDay.getTime()) / (1000 * 60 * 60 * 24))
  const timeStr = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  
  if (diffDays === 0) return `Сегодня в ${timeStr}`
  if (diffDays === 1) return `Завтра в ${timeStr}`
  if (diffDays === -1) return `Вчера в ${timeStr}`
  if (diffDays > 1 && diffDays <= 6) {
    const days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
    return `${days[date.getDay()]} в ${timeStr}`
  }
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const getFullDateTooltip = (dateStr?: string | null) => {
  if (!dateStr) return 'Без даты'
  return new Date(dateStr).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const getPriorityIcon = (priority: string) => {
  const map: Record<string, string> = { high: '🔴', medium: '🟡', low: '🟢' }
  return map[priority] || '⚪'
}

const getPriorityLabel = (priority: string) => {
  return TASK_PRIORITIES.find((item) => item.value === priority)?.label || priority
}
</script>

<template>
  <div class="tasks-dashboard">
    <div class="tasks-top-controls">
      <div class="controls-main-row">
        <button
          type="button"
          class="btn btn-primary create-task-btn"
          aria-label="Создать задачу"
          @click="openCreateModal"
          :title="`Создать задачу (${userStore.profile?.task_hotkey || 'Ctrl+Q'})`"
        >
          <svg class="btn-icon mobile-only" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          <span class="btn-text">+ Создать задачу</span>
        </button>
        
        <TaskSearch :result-count="filteredAndSortedTasks.length" />

        <div class="controls-right">
          <button
            type="button"
            class="btn btn-secondary"
            :aria-expanded="showFilters"
            :aria-label="showFilters ? 'Скрыть фильтры' : 'Показать фильтры'"
            @click="showFilters = !showFilters"
          >
            <svg class="btn-icon mobile-only" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
            <span class="btn-text">{{ showFilters ? 'Скрыть' : 'Фильтры' }}</span>
            <svg class="dropdown-icon" :class="{'icon-rotated': showFilters}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
          </button>
          <button
            type="button"
            class="btn btn-secondary"
            aria-label="Управление категориями"
            @click="showCatModal = true"
          >
            <svg class="btn-icon mobile-only" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
            <span class="btn-text">Категории</span>
          </button>
        </div>
      </div>

      <div v-if="showFilters" class="filters-panel">
        <TaskFiltersPanel
          id-prefix="list"
          :manual-sort="isManualSort"
          @reset-manual-sort="isManualSort = false"
        />
      </div>
    </div>

    <div class="tasks-main">
      <div class="tasks-header-row">
        <div></div>
        <div>Дата</div>
        <div class="priority-wrapper" title="Приоритет">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: var(--color-text-light-2);"></span>
        </div>
        <div>Задача</div>
        <div>Категория</div>
        <div style="text-align: right">Действия</div>
      </div>

      <div v-if="store.isLoading" style="text-align: center; padding: 2rem;">Загрузка...</div>
      
      <div v-else-if="filteredAndSortedTasks.length === 0" class="tasks-empty-state">
        <template v-if="isSearchActive">
          <strong>Совпадений не найдено</strong>
          <span>Измените запрос или активные фильтры.</span>
          <button type="button" class="empty-state-reset" @click="store.filters.searchQuery = ''">Очистить поиск</button>
        </template>
        <span v-else>Задач не найдено</span>
      </div>

      <draggable
        v-model="draggableTasks"
        item-key="id"
        handle=".drag-handle"
        animation="200"
        ghost-class="ghost-task"
      >
        <template #item="{ element: task }">
          <div 
            class="task-item"
            :class="{ 'is-completed': task.status === 'completed' }"
          >
            <div class="drag-handle" title="Потяните для сортировки">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 8h16M4 16h16"/></svg>
            </div>
            <div class="task-date" :title="getFullDateTooltip(task.due_at)">
              {{ formatDate(task.due_at) }}
              <svg v-if="task.recurrence_rule" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" title="Регулярная задача" style="vertical-align: text-bottom; margin-left: 4px; color: var(--color-text-light-2);"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 014-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>
            </div>
            <div class="priority-wrapper">
              <span class="priority-dot" :title="getPriorityLabel(task.priority)">
                {{ getPriorityIcon(task.priority) }}
              </span>
            </div>
            
            <div class="task-text-container">
              <div :id="`task-description-${task.id}`" class="task-text">
                <template
                  v-for="(segment, index) in getHighlightedSegments(getVisibleTaskDescription(task))"
                  :key="`${task.id}-${index}`"
                >
                  <mark v-if="segment.isMatch" class="search-match">{{ segment.text }}</mark>
                  <template v-else>{{ segment.text }}</template>
                </template>
              </div>
              <button
                v-if="canToggleTaskDescription(task)"
                type="button"
                class="expand-text-btn"
                :aria-controls="`task-description-${task.id}`"
                :aria-expanded="expandedTasks.has(task.id)"
                :aria-label="expandedTasks.has(task.id) ? 'Свернуть описание задачи' : 'Показать описание задачи полностью'"
                :title="expandedTasks.has(task.id) ? 'Свернуть описание' : 'Показать полностью'"
                @click.stop="toggleTaskText(task.id)"
              >
                <svg v-if="!expandedTasks.has(task.id)" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15l-6-6-6 6"/></svg>
              </button>
            </div>

            <div class="task-category">
              <span v-if="task.category" class="category-badge" :style="getCategoryStyle(task.category.name)">{{ task.category.name }}</span>
              <span v-else class="category-badge" style="opacity: 0.5">—</span>
            </div>
            <div class="task-actions">
              <button class="action-icon" @click="openEditModal(task)" title="Редактировать">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="action-icon complete" @click="toggleStatus(task)" :title="task.status === 'completed' ? 'Вернуть' : 'Завершить'">
                <svg v-if="task.status !== 'completed'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1018 0 9 9 0 00-18 0z"/><path d="M9 12l2 2 4-4"/></svg>
              </button>
            </div>
          </div>
        </template>
      </draggable>
    </div>

    <TaskModal v-if="showTaskModal" :task-to-edit="editingTask" @close="showTaskModal = false" @saved="showTaskModal = false" />
    <CategoryModal v-if="showCatModal" @close="showCatModal = false" />
  </div>
</template>
