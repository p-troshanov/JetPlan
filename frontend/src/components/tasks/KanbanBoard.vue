<!-- frontend/src/components/tasks/KanbanBoard.vue -->
<!-- Группирует задачи по режиму канбана и сохраняет drag, keyboard и touch-перемещения. -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import draggable from 'vuedraggable'
import { useTasksStore } from '@/stores/tasks'
import type { Task } from '@/types'
import {
  TASK_PRIORITIES,
  buildWeekDays,
  filterTasks,
  isTaskInsideWeek,
  moveDueAtToLocalDate,
  toLocalDateKey,
  type KanbanMode,
  type TaskPriority,
} from '@/utils/taskPlanning'

interface KanbanColumn {
  key: string
  title: string
  subtitle?: string
  acceptsDrop: boolean
  tasks: Task[]
}

interface DragEvent {
  item: HTMLElement
}

const props = defineProps<{
  mode: KanbanMode
  referenceDate: Date
}>()

const emit = defineEmits<{
  edit: [task: Task]
  error: [message: string | null]
}>()

const store = useTasksStore()
const pendingTaskIds = ref<Set<number>>(new Set())
const weekDays = computed(() => buildWeekDays(props.referenceDate))

const visibleTasks = computed(() => filterTasks(store.tasks, store.filters, {
  ignoreHideFuture: props.mode === 'date',
}))

const getTaskColumnKey = (task: Task): string => {
  if (props.mode === 'priority') {
    const priority = TASK_PRIORITIES.some((item) => item.value === task.priority)
      ? task.priority
      : 'medium'
    return `priority:${priority}`
  }

  if (props.mode === 'category') {
    const hasOwnedCategory = store.categories.some((category) => category.id === task.category_id)
    return hasOwnedCategory ? `category:${task.category_id}` : 'category:none'
  }

  if (!task.due_at) return 'date:none'
  if (!isTaskInsideWeek(task, weekDays.value)) return 'date:outside'
  return `date:${toLocalDateKey(new Date(task.due_at))}`
}

const columnDefinitions = computed<Omit<KanbanColumn, 'tasks'>[]>(() => {
  if (props.mode === 'priority') {
    return TASK_PRIORITIES.map((priority) => ({
      key: `priority:${priority.value}`,
      title: priority.label,
      subtitle: 'приоритет',
      acceptsDrop: true,
    }))
  }

  if (props.mode === 'category') {
    return [
      { key: 'category:none', title: 'Без категории', subtitle: 'входящие', acceptsDrop: true },
      ...store.categories.map((category) => ({
        key: `category:${category.id}`,
        title: category.name,
        subtitle: 'категория',
        acceptsDrop: true,
      })),
    ]
  }

  return [
    ...weekDays.value.map((day) => ({
      key: `date:${day.key}`,
      title: day.label,
      subtitle: day.shortLabel,
      acceptsDrop: true,
    })),
    { key: 'date:none', title: 'Без даты', subtitle: 'можно запланировать', acceptsDrop: true },
    { key: 'date:outside', title: 'Вне недели', subtitle: 'перенесите в ближайшие дни', acceptsDrop: false },
  ]
})

const columns = computed<KanbanColumn[]>(() => columnDefinitions.value.map((column) => ({
  ...column,
  tasks: visibleTasks.value.filter((task) => getTaskColumnKey(task) === column.key),
})))

const getMovePatch = (task: Task, targetKey: string): Partial<Task> => {
  const [kind, value] = targetKey.split(':')

  if (kind === 'priority') {
    const priority = value as TaskPriority
    if (!TASK_PRIORITIES.some((item) => item.value === priority)) {
      throw new Error('Неизвестный приоритет')
    }
    return { priority }
  }

  if (kind === 'category') {
    if (value === 'none') return { category_id: null }
    const categoryId = Number(value)
    if (!store.categories.some((category) => category.id === categoryId)) {
      throw new Error('Категория больше недоступна')
    }
    return { category_id: categoryId }
  }

  if (kind === 'date') {
    if (value === 'none') return { due_at: null }
    if (value === 'outside') throw new Error('Колонка «Вне недели» доступна только для просмотра')
    if (!value) throw new Error('Некорректная дата назначения')
    return { due_at: moveDueAtToLocalDate(task.due_at, value) }
  }

  throw new Error('Неизвестное назначение')
}

const moveTask = async (task: Task, targetKey: string) => {
  if (getTaskColumnKey(task) === targetKey || pendingTaskIds.value.has(task.id)) return

  const nextPending = new Set(pendingTaskIds.value)
  nextPending.add(task.id)
  pendingTaskIds.value = nextPending
  emit('error', null)

  try {
    const patch = getMovePatch(task, targetKey)
    await store.updateTaskOptimistically(task.id, patch)
  } catch (error) {
    emit('error', error instanceof Error ? error.message : 'Не удалось переместить задачу')
  } finally {
    const remaining = new Set(pendingTaskIds.value)
    remaining.delete(task.id)
    pendingTaskIds.value = remaining
  }
}

const handleDrop = (event: DragEvent, targetKey: string) => {
  const taskId = Number(event.item.dataset.taskId)
  const task = store.tasks.find((item) => item.id === taskId)
  if (task) void moveTask(task, targetKey)
}

const handleSelectMove = (task: Task, event: Event) => {
  const select = event.currentTarget as HTMLSelectElement
  void moveTask(task, select.value)
}

const formatTaskDate = (dueAt?: string | null) => {
  if (!dueAt) return 'Без даты'
  return new Date(dueAt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getPriorityLabel = (priority: string) => (
  TASK_PRIORITIES.find((item) => item.value === priority)?.label || priority
)
</script>

<template>
  <div class="kanban-scroll" :class="`kanban-${mode}`">
    <section
      v-for="column in columns"
      :key="`${mode}-${column.key}`"
      class="kanban-column"
      :class="{ 'is-readonly': !column.acceptsDrop }"
      :aria-labelledby="`kanban-column-${column.key.replace(':', '-')}`"
    >
      <header class="kanban-column-header">
        <div>
          <h2 :id="`kanban-column-${column.key.replace(':', '-')}`">{{ column.title }}</h2>
          <span>{{ column.subtitle }}</span>
        </div>
        <span class="kanban-count" :aria-label="`Задач: ${column.tasks.length}`">{{ column.tasks.length }}</span>
      </header>

      <draggable
        :list="column.tasks"
        item-key="id"
        class="kanban-column-body"
        :class="{ 'is-empty': column.tasks.length === 0 }"
        :group="{ name: `jetplan-${mode}`, pull: true, put: column.acceptsDrop }"
        :sort="false"
        handle=".kanban-drag-handle"
        ghost-class="kanban-card-ghost"
        chosen-class="kanban-card-chosen"
        :animation="180"
        :delay="120"
        :delay-on-touch-only="true"
        @add="handleDrop($event, column.key)"
      >
        <template #item="{ element: task }">
          <article
            class="kanban-card"
            :class="{ 'is-completed': task.status === 'completed', 'is-pending': pendingTaskIds.has(task.id) }"
            :data-task-id="task.id"
            :aria-busy="pendingTaskIds.has(task.id)"
          >
            <div class="kanban-card-topline">
              <button class="kanban-drag-handle" type="button" title="Перетащить задачу" aria-label="Перетащить задачу">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="9" cy="6" r="1"></circle><circle cx="15" cy="6" r="1"></circle>
                  <circle cx="9" cy="12" r="1"></circle><circle cx="15" cy="12" r="1"></circle>
                  <circle cx="9" cy="18" r="1"></circle><circle cx="15" cy="18" r="1"></circle>
                </svg>
              </button>
              <span class="kanban-priority-badge" :class="`priority-${task.priority}`">
                {{ getPriorityLabel(task.priority) }}
              </span>
              <button class="kanban-edit" type="button" @click="$emit('edit', task)">Изменить</button>
            </div>

            <p class="kanban-card-title" :title="task.description">{{ task.description }}</p>

            <div class="kanban-card-meta">
              <span>{{ formatTaskDate(task.due_at) }}</span>
              <span>{{ task.category?.name || 'Без категории' }}</span>
            </div>

            <label class="kanban-move-control">
              <span>Переместить</span>
              <select
                :value="column.key"
                :disabled="pendingTaskIds.has(task.id)"
                :aria-label="`Переместить задачу «${task.description}»`"
                @change="handleSelectMove(task, $event)"
              >
                <option
                  v-for="target in columnDefinitions"
                  :key="target.key"
                  :value="target.key"
                  :disabled="!target.acceptsDrop"
                >
                  {{ target.title }}
                </option>
              </select>
            </label>
          </article>
        </template>

        <template #footer>
          <div v-if="column.tasks.length === 0" class="kanban-column-empty">
            {{ column.acceptsDrop ? 'Перетащите задачу сюда' : 'Задач вне недели нет' }}
          </div>
        </template>
      </draggable>
    </section>
  </div>
</template>
