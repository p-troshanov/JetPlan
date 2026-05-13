// frontend/src/types/index.ts
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
  category_id?: number;
  due_at?: string;
  priority: 'low' | 'medium' | 'high' | string;
  status: 'pending' | 'completed' | 'cancelled' | string;
  order_index: number;
  created_at: string;
  category?: Category;
  reminder_enabled?: boolean;
  reminder_minutes?: number;
}
