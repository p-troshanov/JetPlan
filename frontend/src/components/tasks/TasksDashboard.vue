// frontend/src/components/tasks/TasksDashboard.vue
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { useUserStore } from '@/stores/user'
import draggable from 'vuedraggable'
import type { Task } from '@/types'
import '@/assets/tasks.css'

import TaskModal from './TaskModal.vue'
import CategoryModal from './CategoryModal.vue'

const store = useTasksStore()
const userStore = useUserStore()

// Модалки
const showTaskModal = ref(false)
const showCatModal = ref(false)
const editingTask = ref<Task | null>(null)

// Видимость блока фильтров
const showFilters = ref(false)

// AI Поиск
const aiQuery = ref('')
const isAiLoading = ref(false)

// Фильтры и сортировка
const isManualSort = ref(false)
const hideFutureTasks = ref(true)
const showOnlyOverdue = ref(false)
const selectedDate = ref('')
const selectedCategoryId = ref<number | ''>('')
const selectedPriority = ref('')
const selectedStatus = ref('pending')

// Интервал фонового обновления
let pollInterval: ReturnType<typeof setInterval> | undefined

const syncOnFocus = () => {
  if (!showTaskModal.value && !showCatModal.value) {
    store.fetchTasks(true) // фоновая загрузка, чтобы UI не мигал
  }
}

onMounted(async () => {
  await userStore.fetchProfile()
  await store.fetchCategories()
  await store.fetchTasks()
  window.addEventListener('keydown', handleGlobalKeydown)
  
  window.addEventListener('focus', syncOnFocus)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') syncOnFocus()
  })

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
  document.removeEventListener('visibilitychange', syncOnFocus)
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

const handleAiQuery = async () => {
  if (!aiQuery.value.trim()) return
  isAiLoading.value = true
  try {
    const localTime = new Date().toLocaleString('ru-RU')
    const response = await store.sendAiQuery(aiQuery.value, localTime)
    
    if (response.action === 'reload') {
      await store.fetchTasks()
      alert(response.message || 'Действие выполнено')
      aiQuery.value = ''
    } else if (response.action === 'filter') {
      showFilters.value = true
      const f = response.filters || {}
      selectedStatus.value = f.status || 'all'
      selectedPriority.value = f.priority || ''
      selectedCategoryId.value = f.category_id ?? ''
      showOnlyOverdue.value = !!f.is_overdue
    }
  } catch (err: any) {
    alert(err.message || 'Ошибка обработки AI запроса')
  } finally {
    isAiLoading.value = false
  }
}

const priorityWeight: Record<string, number> = { high: 3, medium: 2, low: 1 }

const filteredAndSortedTasks = computed(() => {
  let result = [...store.tasks]
  const now = new Date()

  if (hideFutureTasks.value && !showOnlyOverdue.value) {
    const today = new Date(now)
    today.setHours(0, 0, 0, 0)
    result = result.filter(t => {
      if (!t.due_at) return true
      const taskDate = new Date(t.due_at)
      taskDate.setHours(0, 0, 0, 0)
      return taskDate <= today
    })
  }
  
  if (showOnlyOverdue.value) {
    result = result.filter(t => {
      if (!t.due_at) return false
      return new Date(t.due_at).getTime() < now.getTime() && t.status !== 'completed'
    })
  }

  if (selectedDate.value) {
    result = result.filter(t => t.due_at && t.due_at.startsWith(selectedDate.value))
  }

  if (selectedCategoryId.value !== '') {
    result = result.filter(t => t.category_id === selectedCategoryId.value)
  }

  if (selectedPriority.value) {
    result = result.filter(t => t.priority === selectedPriority.value)
  }
  
  if (selectedStatus.value !== 'all') {
    result = result.filter(t => t.status === selectedStatus.value)
  }

  if (isManualSort.value && !showOnlyOverdue.value) {
    result.sort((a, b) => a.order_index - b.order_index)
  } else {
    result.sort((a, b) => {
      const dateA = a.due_at ? new Date(a.due_at).getTime() : new Date(a.created_at).getTime()
      const dateB = b.due_at ? new Date(b.due_at).getTime() : new Date(b.created_at).getTime()
      if (dateB !== dateA) return dateB - dateA
      const pA = priorityWeight[a.priority] || 0
      const pB = priorityWeight[b.priority] || 0
      return pB - pA
    })
  }

  return result
})

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

const formatDate = (dateStr?: string) => {
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

const getFullDateTooltip = (dateStr?: string) => {
  if (!dateStr) return 'Без даты'
  return new Date(dateStr).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const getPriorityIcon = (priority: string) => {
  const map: Record<string, string> = { high: '🔴', medium: '🟡', low: '🟢' }
  return map[priority] || '⚪'
}

const getPriorityLabel = (priority: string) => {
  const map: Record<string, string> = { high: 'Высокий', medium: 'Средний', low: 'Низкий' }
  return map[priority] || priority
}
</script>

<template>
  <div class="tasks-dashboard">
    <div class="tasks-top-controls">
      <div class="controls-main-row">
        <button class="btn btn-primary create-task-btn" @click="openCreateModal" :title="userStore.profile?.task_hotkey || 'Ctrl+Q'">
          <svg class="btn-icon mobile-only" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          <span class="btn-text">+ Создать задачу</span>
        </button>
        
        <div class="ai-search-bar" style="display: flex; gap: 0.5rem; flex: 1; max-width: 400px; margin-left: 1rem;">
          <input type="text" v-model="aiQuery" @keyup.enter="handleAiQuery" class="form-control" placeholder="✨ AI: 'покажи просроченные'..." :disabled="isAiLoading" />
          <button class="btn btn-secondary" @click="handleAiQuery" :disabled="isAiLoading">
            <span v-if="isAiLoading">...</span>
            <span v-else>✨</span>
          </button>
        </div>

        <div class="controls-right">
          <button class="btn btn-secondary" @click="showFilters = !showFilters">
            <svg class="btn-icon mobile-only" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
            <span class="btn-text">{{ showFilters ? 'Скрыть' : 'Фильтры' }}</span>
            <svg class="dropdown-icon" :class="{'icon-rotated': showFilters}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
          </button>
          <button class="btn btn-secondary" @click="showCatModal = true">
            <svg class="btn-icon mobile-only" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
            <span class="btn-text">Категории</span>
          </button>
        </div>
      </div>

      <div v-if="showFilters" class="filters-panel">
        <div class="filters-grid">
          <div class="filter-group">
            <label>Статус</label>
            <select v-model="selectedStatus" class="form-control">
              <option value="pending">Активные</option>
              <option value="completed">Выполненные</option>
              <option value="all">Все</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Дата</label>
            <input type="date" v-model="selectedDate" class="form-control" />
          </div>
          <div class="filter-group">
            <label>Категория</label>
            <select v-model="selectedCategoryId" class="form-control">
              <option value="">Все категории</option>
              <option v-for="cat in store.categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Приоритет</label>
            <select v-model="selectedPriority" class="form-control">
              <option value="">Любой</option>
              <option value="high">Высокий</option>
              <option value="medium">Средний</option>
              <option value="low">Низкий</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Отображение</label>
            <label class="checkbox-label" style="margin-top: 0.5rem">
              <input type="checkbox" v-model="hideFutureTasks" />
              Скрыть будущие
            </label>
            <label class="checkbox-label" style="margin-top: 0.5rem">
              <input type="checkbox" v-model="showOnlyOverdue" />
              Только просроченные
            </label>
          </div>
          <div class="filter-group" v-if="isManualSort">
            <label>Сортировка</label>
            <button class="btn btn-secondary btn-small" @click="isManualSort = false">Сбросить ручную</button>
          </div>
        </div>
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
      
      <div v-else-if="filteredAndSortedTasks.length === 0" style="text-align: center; padding: 2rem; color: var(--color-text-light-2);">
        Задач не найдено
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
            <div class="task-text">{{ task.description }}</div>
            <div>
              <span v-if="task.category" class="category-badge">{{ task.category.name }}</span>
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
