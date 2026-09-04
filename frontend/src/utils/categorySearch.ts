// frontend/src/utils/categorySearch.ts
// Нормализует и фильтрует категории для доступного поиска в форме задачи.
import type { Category } from '@/types'


export const categorySearchText = (category: Category) => (
  [category.name, category.subcategory]
    .filter(Boolean)
    .join(' ')
    .normalize('NFKC')
    .toLocaleLowerCase('ru-RU')
)

export const filterTaskCategories = (categories: Category[], query: string) => {
  const normalizedQuery = query.normalize('NFKC').trim().toLocaleLowerCase('ru-RU')
  if (!normalizedQuery) return categories
  return categories.filter((category) => categorySearchText(category).includes(normalizedQuery))
}
