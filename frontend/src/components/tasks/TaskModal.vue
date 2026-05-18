// frontend/src/components/tasks/TaskModal.vue
<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
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
  due_date: '',
  due_time: '',
  priority: 'medium',
  status: 'pending',
  reminder_enabled: false,
  reminder_minutes: 0,
  recurrence_rule: ''
})

const handleEsc = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    emit('close')
  }
}

const adjustHeight = () => {
  if (descInput.value) {
    descInput.value.style.height = 'auto'
    descInput.value.style.height = `${descInput.value.scrollHeight}px`
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleEsc)

  if (props.taskToEdit) {
    formData.value = {
      description: props.taskToEdit.description,
      category_id: props.taskToEdit.category_id || '',
      due_date: '',
      due_time: '',
      priority: props.taskToEdit.priority,
      status: props.taskToEdit.status,
      reminder_enabled: props.taskToEdit.reminder_enabled ?? false,
      reminder_minutes: props.taskToEdit.reminder_minutes ?? 0,
      recurrence_rule: props.taskToEdit.recurrence_rule || ''
    }

    if (props.taskToEdit.due_at) {
      const d = new Date(props.taskToEdit.due_at)
      const offset = d.getTimezoneOffset() * 60000
      const localIso = new Date(d.getTime() - offset).toISOString()
      formData.value.due_date = localIso.slice(0, 10)
      formData.value.due_time = localIso.slice(11, 16)
    }
  } else {
    // Подставляем текущую дату
    const now = new Date()
    const offset = now.getTimezoneOffset() * 60000
    const localIso = new Date(now.getTime() - offset).toISOString()
    formData.value.due_date = localIso.slice(0, 10)
    formData.value.due_time = localIso.slice(11, 16)
  }
  
  await nextTick()
  if (descInput.value) {
    descInput.value.focus()
    adjustHeight()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEsc)
})

const saveTask = async () => {
  if (!formData.value.description.trim()) return

  const payload: any = { ...formData.value }
  if (payload.category_id === '') payload.category_id = null
  
  if (payload.due_date) {
    const timeStr = payload.due_time || '00:00'
    payload.due_at = new Date(`${payload.due_date}T${timeStr}`).toISOString()
  } else {
    payload.due_at = null
  }
  
  delete payload.due_date
  delete payload.due_time

  if (payload.recurrence_rule === '') payload.recurrence_rule = null

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
        <button class="close-btn" @click="$emit('close')" title="Закрыть (Esc)">&times;</button>
      </div>

      <div class="modal-body">
        <div class="filter-group">
          <label>Текст задачи</label>
          <textarea 
            ref="descInput"
            v-model="formData.description" 
            class="form-control auto-resize-textarea" 
            rows="1" 
            required
            @input="adjustHeight"
            @keydown.ctrl.enter="saveTask"
            @keydown.meta.enter="saveTask"
          ></textarea>
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
          <div style="display: flex; gap: 0.5rem;">
            <input 
              type="date" 
              v-model="formData.due_date" 
              class="form-control" 
              @click="$event.target.showPicker && $event.target.showPicker()"
            />
            <input 
              type="time" 
              v-model="formData.due_time" 
              class="form-control"
              @click="$event.target.showPicker && $event.target.showPicker()" 
            />
          </div>
        </div>

        <div class="filter-group">
          <label>Повтор (Регулярность)</label>
          <select v-model="formData.recurrence_rule" class="form-control">
            <option value="">Без повтора</option>
            <option value="FREQ=DAILY">Каждый день</option>
            <option value="FREQ=WEEKLY">Каждую неделю</option>
            <option value="FREQ=MONTHLY">Каждый месяц</option>
            <option value="FREQ=YEARLY">Каждый год</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Приоритет</label>
          <div class="priority-selector">
            <button 
              type="button" 
              class="priority-circle high" 
              :class="{ selected: formData.priority === 'high' }" 
              @click="formData.priority = 'high'" 
              title="Высокий"
            ></button>
            <button 
              type="button" 
              class="priority-circle medium" 
              :class="{ selected: formData.priority === 'medium' }" 
              @click="formData.priority = 'medium'" 
              title="Средний"
            ></button>
            <button 
              type="button" 
              class="priority-circle low" 
              :class="{ selected: formData.priority === 'low' }" 
              @click="formData.priority = 'low'" 
              title="Низкий"
            ></button>
          </div>
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

      <div class="modal-footer-container">
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
        <div class="modal-hint">Ctrl+Enter для сохранения</div>
      </div>
    </div>
  </div>
</template>
