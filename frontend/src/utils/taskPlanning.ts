// frontend/src/utils/taskPlanning.ts
// Содержит единые правила фильтрации, сортировки и календарного перемещения задач.
import type { Task } from '../types'

export const TASK_PRIORITIES = [
  { value: 'high', label: 'Высокий' },
  { value: 'medium', label: 'Средний' },
  { value: 'low', label: 'Низкий' },
] as const

export type TaskPriority = (typeof TASK_PRIORITIES)[number]['value']
export type TaskStatusFilter = 'pending' | 'completed' | 'all'
export type KanbanMode = 'priority' | 'category' | 'date'

export interface TaskFilters {
  searchQuery: string
  hideFutureTasks: boolean
  showOnlyOverdue: boolean
  selectedDate: string
  selectedCategoryId: number | ''
  selectedPriority: TaskPriority | ''
  selectedStatus: TaskStatusFilter
}

export interface TaskFilterOptions {
  ignoreHideFuture?: boolean
  manualSort?: boolean
  now?: Date
}

export interface WeekDay {
  key: string
  label: string
  shortLabel: string
}

const priorityWeight: Record<string, number> = { high: 3, medium: 2, low: 1 }

export const createDefaultTaskFilters = (): TaskFilters => ({
  searchQuery: '',
  hideFutureTasks: true,
  showOnlyOverdue: false,
  selectedDate: '',
  selectedCategoryId: '',
  selectedPriority: '',
  selectedStatus: 'pending',
})

export const toLocalDateKey = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const startOfLocalDay = (date: Date): Date => {
  const result = new Date(date)
  result.setHours(0, 0, 0, 0)
  return result
}

const getTaskTimestamp = (task: Task): number => {
  const source = task.due_at || task.created_at
  const timestamp = new Date(source).getTime()
  return Number.isNaN(timestamp) ? 0 : timestamp
}

export const filterTasks = (
  tasks: Task[],
  filters: TaskFilters,
  options: TaskFilterOptions = {},
): Task[] => {
  let result = [...tasks]
  const now = options.now ? new Date(options.now) : new Date()
  const normalizedSearch = filters.searchQuery.trim().toLocaleLowerCase('ru-RU')

  if (filters.hideFutureTasks && !filters.showOnlyOverdue && !options.ignoreHideFuture) {
    const today = startOfLocalDay(now).getTime()
    result = result.filter((task) => {
      if (!task.due_at) return true
      const dueDate = new Date(task.due_at)
      return !Number.isNaN(dueDate.getTime()) && startOfLocalDay(dueDate).getTime() <= today
    })
  }

  if (filters.showOnlyOverdue) {
    result = result.filter((task) => (
      Boolean(task.due_at)
      && new Date(task.due_at as string).getTime() < now.getTime()
      && task.status !== 'completed'
    ))
  }

  if (filters.selectedDate) {
    result = result.filter((task) => (
      Boolean(task.due_at)
      && toLocalDateKey(new Date(task.due_at as string)) === filters.selectedDate
    ))
  }

  if (filters.selectedCategoryId !== '') {
    result = result.filter((task) => task.category_id === filters.selectedCategoryId)
  }

  if (filters.selectedPriority) {
    result = result.filter((task) => task.priority === filters.selectedPriority)
  }

  if (filters.selectedStatus !== 'all') {
    result = result.filter((task) => task.status === filters.selectedStatus)
  }

  if (normalizedSearch) {
    result = result.filter((task) => (
      task.description.toLocaleLowerCase('ru-RU').includes(normalizedSearch)
    ))
  }

  if (options.manualSort && !filters.showOnlyOverdue) {
    return result.sort((left, right) => left.order_index - right.order_index)
  }

  return result.sort((left, right) => {
    const dateDifference = getTaskTimestamp(right) - getTaskTimestamp(left)
    if (dateDifference !== 0) return dateDifference
    return (priorityWeight[right.priority] || 0) - (priorityWeight[left.priority] || 0)
  })
}

export const buildWeekDays = (startDate: Date = new Date()): WeekDay[] => {
  const start = startOfLocalDay(startDate)

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)

    return {
      key: toLocalDateKey(date),
      label: index === 0
        ? 'Сегодня'
        : date.toLocaleDateString('ru-RU', { weekday: 'long' }),
      shortLabel: date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }),
    }
  })
}

export const moveDueAtToLocalDate = (
  currentDueAt: string | null | undefined,
  targetDateKey: string,
): string => {
  const [year, month, day] = targetDateKey.split('-').map(Number)
  if (!year || !month || !day) throw new Error('Некорректная дата назначения')

  const current = currentDueAt ? new Date(currentDueAt) : null
  const hasCurrentTime = current !== null && !Number.isNaN(current.getTime())
  const target = new Date(
    year,
    month - 1,
    day,
    hasCurrentTime ? current.getHours() : 9,
    hasCurrentTime ? current.getMinutes() : 0,
    hasCurrentTime ? current.getSeconds() : 0,
    hasCurrentTime ? current.getMilliseconds() : 0,
  )

  if (toLocalDateKey(target) !== targetDateKey) throw new Error('Некорректная дата назначения')
  return target.toISOString()
}

export const isTaskInsideWeek = (task: Task, weekDays: WeekDay[]): boolean => {
  if (!task.due_at) return false
  const taskDate = new Date(task.due_at)
  if (Number.isNaN(taskDate.getTime())) return false
  return weekDays.some((day) => day.key === toLocalDateKey(taskDate))
}
