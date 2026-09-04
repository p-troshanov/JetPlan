<!-- frontend/src/components/tasks/CategoryCombobox.vue -->
<!-- Даёт доступный поиск и выбор категории при создании или редактировании задачи. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { Category } from '@/types'
import { filterTaskCategories } from '@/utils/categorySearch'

const props = defineProps<{
  modelValue: number | ''
  categories: Category[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | '']
}>()

const input = ref<HTMLInputElement | null>(null)
const query = ref('')
const isOpen = ref(false)
const activeIndex = ref(0)
const listboxId = `category-options-${Math.random().toString(36).slice(2)}`

const selectedCategory = computed(() => (
  props.categories.find((category) => category.id === props.modelValue) ?? null
))

const effectiveQuery = computed(() => (
  query.value === selectedCategory.value?.name ? '' : query.value
))

const filteredCategories = computed(() => (
  filterTaskCategories(props.categories, effectiveQuery.value)
))

const optionsCount = computed(() => filteredCategories.value.length + 1)

const syncQuery = () => {
  query.value = selectedCategory.value?.name ?? ''
}

watch(() => [props.modelValue, props.categories] as const, syncQuery, { immediate: true, deep: true })

const open = async () => {
  isOpen.value = true
  activeIndex.value = selectedCategory.value
    ? Math.max(1, filteredCategories.value.findIndex((category) => category.id === selectedCategory.value?.id) + 1)
    : 0
  await nextTick()
  input.value?.select()
}

const close = () => {
  isOpen.value = false
  syncQuery()
}

const selectCategory = (category: Category | null) => {
  emit('update:modelValue', category?.id ?? '')
  query.value = category?.name ?? ''
  isOpen.value = false
}

const onInput = () => {
  isOpen.value = true
  activeIndex.value = 0
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (!isOpen.value) {
      void open()
      return
    }
    activeIndex.value = (activeIndex.value + 1) % optionsCount.value
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (!isOpen.value) {
      void open()
      return
    }
    activeIndex.value = (activeIndex.value - 1 + optionsCount.value) % optionsCount.value
  } else if (event.key === 'Enter' && isOpen.value) {
    event.preventDefault()
    const category = activeIndex.value === 0
      ? null
      : filteredCategories.value[activeIndex.value - 1] ?? null
    selectCategory(category)
  } else if (event.key === 'Escape' && isOpen.value) {
    event.preventDefault()
    close()
  }
}

const onFocusOut = (event: FocusEvent) => {
  const nextTarget = event.relatedTarget
  if (!(nextTarget instanceof Node) || !(event.currentTarget as HTMLElement).contains(nextTarget)) {
    close()
  }
}
</script>

<template>
  <div class="category-combobox" @focusout="onFocusOut">
    <div class="category-combobox-control">
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input
        ref="input"
        v-model="query"
        type="text"
        role="combobox"
        aria-autocomplete="list"
        :aria-expanded="isOpen"
        :aria-controls="listboxId"
        :aria-activedescendant="isOpen ? `${listboxId}-${activeIndex}` : undefined"
        autocomplete="off"
        placeholder="Найти категорию"
        @focus="open"
        @click="open"
        @input="onInput"
        @keydown="onKeydown"
      />
      <button
        v-if="modelValue !== ''"
        type="button"
        class="category-combobox-clear"
        aria-label="Сбросить категорию"
        title="Без категории"
        @mousedown.prevent
        @click="selectCategory(null)"
      >
        &times;
      </button>
      <svg v-else aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="m7 10 5 5 5-5" />
      </svg>
    </div>

    <ul v-if="isOpen" :id="listboxId" class="category-combobox-options" role="listbox">
      <li
        :id="`${listboxId}-0`"
        role="option"
        :aria-selected="modelValue === ''"
        :class="{ active: activeIndex === 0, selected: modelValue === '' }"
        @mouseenter="activeIndex = 0"
        @mousedown.prevent="selectCategory(null)"
      >
        Без категории
      </li>
      <li
        v-for="(category, index) in filteredCategories"
        :id="`${listboxId}-${index + 1}`"
        :key="category.id"
        role="option"
        :aria-selected="modelValue === category.id"
        :class="{ active: activeIndex === index + 1, selected: modelValue === category.id }"
        @mouseenter="activeIndex = index + 1"
        @mousedown.prevent="selectCategory(category)"
      >
        <span>{{ category.name }}</span>
        <small v-if="category.subcategory">{{ category.subcategory }}</small>
      </li>
      <li v-if="filteredCategories.length === 0" class="category-combobox-empty" aria-disabled="true">
        Совпадений нет
      </li>
    </ul>
  </div>
</template>
