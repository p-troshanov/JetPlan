// frontend/tests/categorySearch.test.ts
// Проверяет регистронезависимый поиск категорий по названию и подкатегории.
import assert from 'node:assert/strict'
import test from 'node:test'
import type { Category } from '../src/types/index.ts'
import { filterTaskCategories } from '../src/utils/categorySearch.ts'


const categories: Category[] = [
  { id: 1, user_id: 7, name: 'Работа', subcategory: 'Проекты', category_type: 'custom' },
  { id: 2, user_id: 7, name: 'Личное', subcategory: 'Дом', category_type: 'default' },
  { id: 3, user_id: 7, name: 'Покупки', category_type: 'custom' },
]

test('пустой запрос сохраняет исходный порядок категорий', () => {
  assert.deepEqual(filterTaskCategories(categories, '  ').map((category) => category.id), [1, 2, 3])
})

test('поиск не зависит от регистра и учитывает подкатегорию', () => {
  assert.deepEqual(filterTaskCategories(categories, 'РАБ').map((category) => category.id), [1])
  assert.deepEqual(filterTaskCategories(categories, 'дом').map((category) => category.id), [2])
})

test('несуществующая категория возвращает пустой список', () => {
  assert.deepEqual(filterTaskCategories(categories, 'спорт'), [])
})
