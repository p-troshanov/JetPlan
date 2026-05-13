// frontend/src/stores/user.ts
import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface UserProfile {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  ai_provider?: string;
  ai_api_key?: string;
  task_hotkey?: string;
  telegram_id?: number;
}

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfile | null>(null)
  
  const getHeaders = () => {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  const fetchProfile = async () => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    try {
      const res = await fetch('/api/auth/me', { headers: getHeaders() })
      if (res.ok) {
        profile.value = await res.json()
      }
    } catch (err) {
      console.error('Error fetching profile:', err)
    }
  }

  const updateProfile = async (data: Partial<UserProfile>) => {
    try {
      const res = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data)
      })
      if (res.ok) {
        profile.value = await res.json()
        return true
      }
    } catch (err) {
      console.error('Error updating profile:', err)
    }
    return false
  }

  return { profile, fetchProfile, updateProfile, getHeaders }
})
