// frontend/src/utils/taskDescription.ts
// Формирует законченный по смыслу preview описания задачи для компактного списка.

export const TASK_DESCRIPTION_PREVIEW_LENGTH = 150

export interface TaskDescriptionPreview {
  text: string
  isTruncated: boolean
}

const SENTENCE_END_PATTERN = /[.!?…]+(?:["'»”’\)\]]+)?(?=\s|$)/gu

export const buildTaskDescriptionPreview = (
  description: string,
  targetLength = TASK_DESCRIPTION_PREVIEW_LENGTH,
): TaskDescriptionPreview => {
  const content = description.trimEnd()

  if (content.length <= targetLength) {
    return { text: description, isTruncated: false }
  }

  let lastBoundaryWithinTarget: number | null = null
  let firstBoundaryAfterTarget: number | null = null

  for (const match of content.matchAll(SENTENCE_END_PATTERN)) {
    const boundary = (match.index ?? 0) + match[0].length
    const hasMoreText = content.slice(boundary).trim().length > 0

    if (!hasMoreText) continue

    if (boundary <= targetLength) {
      lastBoundaryWithinTarget = boundary
      continue
    }

    firstBoundaryAfterTarget = boundary
    break
  }

  const boundary = lastBoundaryWithinTarget ?? firstBoundaryAfterTarget
  if (boundary === null) {
    return { text: description, isTruncated: false }
  }

  return {
    text: content.slice(0, boundary).trimEnd(),
    isTruncated: true,
  }
}
