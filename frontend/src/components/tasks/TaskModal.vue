// frontend/src/components/tasks/TaskModal.vue
<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import type { Task } from '@/types'

const props = defineProps<{
  taskToEdit?: Task | null
}>()

const emit = defineEmits(['close', 'saved'])
const store = useTasksStore()

const descInput = ref<HTMLTextAreaElement | null>(null)

const formData = ref({
  description: '',
  category_id: '' as number | '',
  due_at: '',
  priority: 'medium',
  status: 'pending',
  reminder_enabled: false,
  reminder_minutes: 0
})

// Функция для правильного конвертирования даты в локальное время инпута (YYYY-MM-DDTHH:mm)
const getLocalISOTime = (dateInput: Date | string) => {
  const date = new Date(dateInput)
  if (isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60000
  return (new Date(date.getTime() - offset)).toISOString().slice(0, 16)
}

onMounted(async () => {
  if (props.taskToEdit) {
    formData.value = {
      description: props.taskToEdit.description,
      category_id: props.taskToEdit.category_id || '',
      // Конвертируем UTC время с сервера в локальное время для инпута
      due_at: props.taskToEdit.due_at ? getLocalISOTime(props.taskToEdit.due_at) : '',
      priority: props.taskToEdit.priority,
      status: props.taskToEdit.status,
      // Безопасное присвоение
      reminder_enabled: props.taskToEdit.reminder_enabled ?? false,
      reminder_minutes: props.taskToEdit.reminder_minutes ?? 0
    }
  } else {
    // Подставляем текущее время (с учетом часового пояса устройства)
    formData.value.due_at = getLocalISOTime(new Date())
  }
  
  // Автофокус на поле ввода текста задачи
  await nextTick()
  if (descInput.value) {
    descInput.value.focus()
  }
})

const saveTask = async () => {
  if (!formData.value.description.trim()) return

  const payload: any = { ...formData.value }
  if (payload.category_id === '') payload.category_id = null
  if (payload.due_at === '') payload.due_at = null
  else payload.due_at = new Date(payload.due_at).toISOString()

  // Явное приведение типов перед отправкой на бэкенд
  payload.reminder_enabled = Boolean(payload.reminder_enabled)
  payload.reminder_minutes = Number(payload.reminder_minutes) || 0

  try {
    if (props.taskToEdit) {
      await store.updateTask(props.taskToEdit.id, payload)
    } else {
      await store.createTask(payload)
    }
    emit('saved')
  } catch (e) {
    console.error(e)
  }
}

const deleteTask = async () => {
  if (props.taskToEdit && confirm('Точно удалить задачу?')) {
    await store.deleteTask(props.taskToEdit.id)
    emit('saved')
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ taskToEdit ? 'Редактировать задачу' : 'Новая задача' }}</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div class="filter-group">
          <label>Текст задачи</label>
          <textarea 
            ref="descInput"
            v-model="formData.description" 
            class="form-control" 
            rows="3" 
            required
            @keydown.ctrl.enter="saveTask"
            @keydown.meta.enter="saveTask"
          ></textarea>
          <small style="color: var(--color-text-light-2); font-size: 0.8rem; margin-top: 0.2rem; display: block;">
            Ctrl+Enter для сохранения
          </small>
        </div>

        <div class="filter-group">
          <label>Категория</label>
          <select v-model="formData.category_id" class="form-control">
            <option value="">Без категории</option>
            <option v-for="cat in store.categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label>Срок выполнения</label>
          <input type="datetime-local" v-model="formData.due_at" class="form-control" />
        </div>

        <div class="filter-group">
          <label>Приоритет</label>
          <select v-model="formData.priority" class="form-control">
            <option value="high">Высокий</option>
            <option value="medium">Средний</option>
            <option value="low">Низкий</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="checkbox-label" style="margin-top: 0.5rem">
            <input type="checkbox" v-model="formData.reminder_enabled" />
            Включить напоминание
          </label>
        </div>

        <div class="filter-group" v-if="formData.reminder_enabled">
          <label>Напомнить за (минут до срока)</label>
          <input type="number" v-model.number="formData.reminder_minutes" class="form-control" min="0" />
        </div>
      </div>

      <div class="modal-footer">
        <div>
          <button v-if="taskToEdit" class="btn btn-danger" style="width: auto; padding: 0.8rem;" @click="deleteTask" title="Удалить">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          </button>
        </div>
        <div style="display: flex; gap: 1rem;">
          <button class="btn btn-secondary" style="width: auto;" @click="$emit('close')">Отмена</button>
          <button class="btn btn-primary" style="width: auto;" @click="saveTask">Сохранить</button>
        </div>
      </div>
    </div>
  </div>
</template>
