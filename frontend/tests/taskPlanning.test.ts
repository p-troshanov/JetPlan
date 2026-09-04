// frontend/tests/taskPlanning.test.ts
// Проверяет общие фильтры и календарные границы недельного канбана без browser runtime.
import assert from 'node:assert/strict'
import test from 'node:test'
import type { Task } from '../src/types/index.ts'
import {
  buildWeekDays,
  createDefaultTaskFilters,
  filterTasks,
  moveDueAtToLocalDate,
  toLocalDateKey,
} from '../src/utils/taskPlanning.ts'

const localIso = (year: number, month: number, day: number, hour = 12, minute = 0) => (
  new Date(year, month - 1, day, hour, minute).toISOString()
)

const makeTask = (id: number, overrides: Partial<Task> = {}): Task => ({
  id,
  user_id: 1,
  description: `Задача ${id}`,
  category_id: null,
  due_at: null,
  priority: 'medium',
  status: 'pending',
  order_index: id,
  created_at: localIso(2026, 9, 1),
  category: null,
  ...overrides,
})

test('общие фильтры скрывают будущие задачи, но недельный режим может показать их', () => {
  const filters = createDefaultTaskFilters()
  const now = new Date(2026, 8, 4, 12, 0)
  const tasks = [
    makeTask(1, { due_at: localIso(2026, 9, 4, 9) }),
    makeTask(2, { due_at: localIso(2026, 9, 6, 9) }),
    makeTask(3),
  ]

  assert.deepEqual(filterTasks(tasks, filters, { now }).map((task) => task.id).sort(), [1, 3])
  assert.deepEqual(
    filterTasks(tasks, filters, { now, ignoreHideFuture: true }).map((task) => task.id).sort(),
    [1, 2, 3],
  )
})

test('поиск, категория, приоритет и статус применяются одним контрактом', () => {
  const filters = createDefaultTaskFilters()
  filters.hideFutureTasks = false
  filters.searchQuery = 'ОТЧЁТ'
  filters.selectedCategoryId = 7
  filters.selectedPriority = 'high'
  filters.selectedStatus = 'pending'

  const tasks = [
    makeTask(1, { description: 'Подготовить отчёт', category_id: 7, priority: 'high' }),
    makeTask(2, { description: 'Подготовить отчёт', category_id: 8, priority: 'high' }),
    makeTask(3, { description: 'Подготовить отчёт', category_id: 7, priority: 'low' }),
    makeTask(4, { description: 'Подготовить отчёт', category_id: 7, priority: 'high', status: 'completed' }),
  ]

  assert.deepEqual(filterTasks(tasks, filters).map((task) => task.id), [1])
})

test('семидневный горизонт корректно пересекает границу года', () => {
  const days = buildWeekDays(new Date(2026, 11, 29, 18, 0))

  assert.deepEqual(days.map((day) => day.key), [
    '2026-12-29',
    '2026-12-30',
    '2026-12-31',
    '2027-01-01',
    '2027-01-02',
    '2027-01-03',
    '2027-01-04',
  ])
})

test('перенос на другую дату сохраняет локальное время на границе месяца и года', () => {
  const original = localIso(2026, 12, 31, 23, 45)
  const moved = new Date(moveDueAtToLocalDate(original, '2027-01-01'))

  assert.equal(toLocalDateKey(moved), '2027-01-01')
  assert.equal(moved.getHours(), 23)
  assert.equal(moved.getMinutes(), 45)
})

test('задача без даты при планировании получает предсказуемое локальное время 09:00', () => {
  const moved = new Date(moveDueAtToLocalDate(null, '2026-09-05'))

  assert.equal(toLocalDateKey(moved), '2026-09-05')
  assert.equal(moved.getHours(), 9)
  assert.equal(moved.getMinutes(), 0)
})
