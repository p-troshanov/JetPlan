// frontend/src/stores/tasks.ts
import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Task, Category } from '../types'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const categories = ref<Category[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const getHeaders = () => {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  // Централизованная обработка 401 ошибки
  const handleUnauthorized = (status: number) => {
    if (status === 401) {
      localStorage.removeItem('access_token')
      window.location.reload()
    }
  }

  // === Категории ===
  const fetchCategories = async () => {
    try {
      const res = await fetch('/api/categories', { headers: getHeaders() })
      handleUnauthorized(res.status)
      if (res.ok) {
        categories.value = await res.json()
      }
    } catch (err) {
      console.error('Error fetching categories:', err)
    }
  }

  const createCategory = async (name: string) => {
    const res = await fetch('/api/categories', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ name, category_type: 'custom' })
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      const newCat = await res.json()
      categories.value.push(newCat)
      return newCat
    }
    throw new Error('Failed to create category')
  }

  const updateCategory = async (id: number, name: string) => {
    const res = await fetch(`/api/categories/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ name })
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      const updatedCat = await res.json()
      const index = categories.value.findIndex(c => c.id === id)
      if (index !== -1) {
        categories.value[index] = updatedCat
      }
      // Синхронизируем название категории в уже загруженных задачах
      tasks.value.forEach(t => {
        if (t.category_id === id && t.category) {
          t.category.name = updatedCat.name
        }
      })
      return updatedCat
    }
    throw new Error('Failed to update category')
  }

  const deleteCategory = async (id: number) => {
    const res = await fetch(`/api/categories/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      categories.value = categories.value.filter(c => c.id !== id)
      // Очищаем удаленную категорию у загруженных задач
      tasks.value.forEach(t => {
        if (t.category_id === id) {
          t.category_id = undefined
          t.category = undefined
        }
      })
    }
  }

  // === Задачи ===
  const fetchTasks = async (isBackground = false) => {
    if (!isBackground) isLoading.value = true
    try {
      const res = await fetch('/api/tasks', { headers: getHeaders() })
      handleUnauthorized(res.status)
      if (res.ok) {
        tasks.value = await res.json()
      }
    } catch (err) {
      error.value = 'Ошибка загрузки задач'
      console.error(err)
    } finally {
      if (!isBackground) isLoading.value = false
    }
  }

  const createTask = async (taskData: Partial<Task>) => {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(taskData)
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      const newTask = await res.json()
      tasks.value.push(newTask)
      return newTask
    }
    throw new Error('Failed to create task')
  }

  const updateTask = async (id: number, taskData: Partial<Task>) => {
    const res = await fetch(`/api/tasks/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(taskData)
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      const updatedTask = await res.json()
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = updatedTask
      }
      return updatedTask
    }
    throw new Error('Failed to update task')
  }

  const deleteTask = async (id: number) => {
    const res = await fetch(`/api/tasks/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      tasks.value = tasks.value.filter(t => t.id !== id)
    }
  }

  const reorderTasks = async (taskIds: number[]) => {
    // Оптимистичное обновление UI
    const orderMap = new Map(taskIds.map((id, index) => [id, index]));
    tasks.value.forEach(task => {
      if (orderMap.has(task.id)) {
        task.order_index = orderMap.get(task.id)!;
      }
    });
    
    // Сортируем массив локально, чтобы соответствовать новому order_index
    tasks.value.sort((a, b) => a.order_index - b.order_index);

    // Отправка на сервер
    const res = await fetch('/api/tasks/reorder', {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ task_ids: taskIds })
    });
    
    handleUnauthorized(res.status)
    
    if (!res.ok) {
      // Если ошибка, заново запрашиваем задачи для синхронизации
      await fetchTasks();
    }
  }

  const sendAiQuery = async (query: string, localTime: string) => {
    const res = await fetch('/api/tasks/ai', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ query, local_time: localTime })
    })
    handleUnauthorized(res.status)
    if (res.ok) {
      return await res.json()
    }
    const errText = await res.text()
    try {
        const errJson = JSON.parse(errText)
        throw new Error(errJson.detail || 'Failed to process AI query')
    } catch (e) {
        throw new Error('Failed to process AI query')
    }
  }

  return {
    tasks, categories, isLoading, error,
    fetchTasks, createTask, updateTask, deleteTask, reorderTasks, sendAiQuery,
    fetchCategories, createCategory, updateCategory, deleteCategory
  }
})

