// frontend/tests/taskDescription.test.ts
// Проверяет осмысленное сокращение описаний задач без обрыва слов и предложений.
import assert from 'node:assert/strict'
import test from 'node:test'
import { buildTaskDescriptionPreview } from '../src/utils/taskDescription.ts'

test('не показывает сокращение, если описание целиком помещается в preview', () => {
  const description = 'Актуализация организаций через яндекс карты, добавление новых организаций, смена статуса отображения если организация "больше не работает"....'

  assert.deepEqual(buildTaskDescriptionPreview(description), {
    text: description,
    isTruncated: false,
  })
})

test('оставляет максимальное число законченных предложений в пределах preview', () => {
  const firstSentence = 'Проверить список организаций.'
  const secondSentence = 'Обновить статусы и добавить новые адреса.'
  const description = `${firstSentence} ${secondSentence} Затем отправить итоговый отчёт владельцу проекта.`

  assert.deepEqual(buildTaskDescriptionPreview(description, 80), {
    text: `${firstSentence} ${secondSentence}`,
    isTruncated: true,
  })
})

test('не обрывает длинное первое предложение ради лимита', () => {
  const firstSentence = 'Проверить очень длинный список организаций и аккуратно обновить все найденные статусы без потери исходных данных.'
  const description = `${firstSentence} Затем подготовить отчёт.`

  assert.deepEqual(buildTaskDescriptionPreview(description, 60), {
    text: firstSentence,
    isTruncated: true,
  })
})

test('показывает длинное описание полностью, если в нём нет границы для безопасного сокращения', () => {
  const description = 'Проверить список организаций и обновить все найденные статусы без потери исходных данных'

  assert.deepEqual(buildTaskDescriptionPreview(description, 40), {
    text: description,
    isTruncated: false,
  })
})

test('сохраняет знак завершения предложения перед закрывающей кавычкой', () => {
  const description = 'Поменять статус на «Больше не работает». Затем обновить карту.'

  assert.deepEqual(buildTaskDescriptionPreview(description, 45), {
    text: 'Поменять статус на «Больше не работает».',
    isTruncated: true,
  })
})
