// frontend/src/components/tasks/CategoryModal.vue
<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '@/stores/tasks'

const emit = defineEmits(['close'])
const store = useTasksStore()
const newCategoryName = ref('')

const editingId = ref<number | null>(null)
const editingName = ref('')

const handleCreate = async () => {
  if (!newCategoryName.value.trim()) return
  await store.createCategory(newCategoryName.value)
  newCategoryName.value = ''
}

const handleDelete = async (id: number) => {
  if (confirm('Удалить категорию?')) {
    await store.deleteCategory(id)
  }
}

const startEdit = (cat: any) => {
  editingId.value = cat.id
  editingName.value = cat.name
}

const saveEdit = async (id: number) => {
  if (!editingName.value.trim()) return
  await store.updateCategory(id, editingName.value)
  editingId.value = null
}

const cancelEdit = () => {
  editingId.value = null
  editingName.value = ''
}
</script>

<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Управление категориями</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div class="filter-group">
          <label>Добавить новую</label>
          <div style="display: flex; gap: 0.5rem;">
            <input v-model="newCategoryName" class="form-control" placeholder="Название категории" @keyup.enter="handleCreate" />
            <button class="btn btn-primary" style="width: auto; padding: 0.8rem 1.2rem;" @click="handleCreate">+</button>
          </div>
        </div>

        <div class="category-list">
          <div v-for="cat in store.categories" :key="cat.id" class="category-list-item">
            <template v-if="editingId === cat.id">
              <input 
                v-model="editingName" 
                class="form-control form-control-sm" 
                @keyup.enter="saveEdit(cat.id)" 
                @keyup.esc="cancelEdit" 
                style="margin-right: 0.5rem;"
                autoFocus 
              />
              <div style="display: flex; gap: 0.25rem;">
                <button class="action-icon" title="Сохранить" @click="saveEdit(cat.id)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                </button>
                <button class="action-icon" title="Отмена" @click="cancelEdit">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </template>
            <template v-else>
              <span>{{ cat.name }}</span>
              <div style="display: flex; gap: 0.25rem;">
                <button class="action-icon" title="Редактировать" @click="startEdit(cat)">
                   <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="action-icon" title="Удалить" @click="handleDelete(cat.id)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
              </div>
            </template>
          </div>
          <div v-if="store.categories.length === 0" style="padding: 1rem; text-align: center; color: var(--color-text-light-2);">
            Нет категорий
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
