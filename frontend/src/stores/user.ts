// frontend/src/stores/user.ts
// Хранит профиль текущего пользователя и выполняет запросы его чтения и обновления.
import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface UserProfile {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  ai_provider?: 'groq' | 'openrouter';
  ai_model?: string | null;
  ai_api_key_configured: boolean;
  stt_provider?: 'groq';
  stt_api_key_configured: boolean;
  task_hotkey?: string;
  auto_postpone_overdue?: boolean;
  telegram_id?: number;
}

export interface UserProfileUpdate {
  first_name?: string;
  last_name?: string;
  ai_provider?: 'groq' | 'openrouter';
  ai_api_key?: string;
  ai_model?: string | null;
  stt_provider?: 'groq';
  stt_api_key?: string;
  task_hotkey?: string;
  auto_postpone_overdue?: boolean;
}

interface ProfileUpdateResult {
  ok: boolean;
  error?: string;
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

  const updateProfile = async (data: UserProfileUpdate): Promise<ProfileUpdateResult> => {
    try {
      const res = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data)
      })
      if (res.ok) {
        profile.value = await res.json()
        return { ok: true }
      }
      const body = await res.json().catch(() => null)
      return { ok: false, error: body?.detail || 'Не удалось сохранить настройки' }
    } catch (err) {
      console.error('Error updating profile:', err)
      return { ok: false, error: 'Сервер недоступен. Повторите позже.' }
    }
  }

  return { profile, fetchProfile, updateProfile, getHeaders }
})
