// frontend/src/types/index.ts
// Описывает общие frontend-типы профиля, категорий и задач.
export interface Category {
  id: number;
  user_id: number;
  name: string;
  subcategory?: string;
  category_type: string;
}

export interface Task {
  id: number;
  user_id: number;
  description: string;
  category_id?: number | null;
  due_at?: string | null;
  priority: 'low' | 'medium' | 'high' | string;
  status: 'pending' | 'completed' | 'cancelled' | string;
  order_index: number;
  created_at: string;
  category?: Category | null;
  reminder_enabled?: boolean;
  reminder_minutes?: number;
  recurrence_rule?: string;
}
