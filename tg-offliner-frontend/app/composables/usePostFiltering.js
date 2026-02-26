/**
 * Composable для фильтрации постов в preview и экспорте
 * Централизованная логика определения видимости постов
 */
export const usePostFiltering = () => {
  /**
   * Проверяет, должно ли медиа быть скрыто (неподдерживаемые форматы для InDesign)
   */
  const shouldHideMedia = (post) => {
    if (!post.media_url) return false

    // Неподдерживаемые типы медиа
    const unsupportedTypes = [
      'MessageMediaWebPage',  // Веб-страницы
    ]

    // Явно неподдерживаемые типы
    if (unsupportedTypes.includes(post.media_type)) {
      return true
    }

    // MessageMediaDocument только если НЕ изображение
    if (post.media_type === 'MessageMediaDocument') {
      if (!post.mime_type || !post.mime_type.startsWith('image/')) {
        return true
      }
    }

    return false
  }

  /**
   * Проверяет, должен ли пост быть скрыт полностью
   */
  const shouldHidePost = (post) => {
    // 1. Пост скрыт в базе через edits
    if (post.isHidden) {
      return true
    }

    // 2. Пост имеет только скрытое медиа и нет текста
    const hasHiddenMedia = shouldHideMedia(post)
    const hasNoText = !post.message || post.message.trim() === ''

    if (hasHiddenMedia && hasNoText) {
      return true
    }

    return false
  }

  /**
   * Применяет фильтры к списку постов
   * Добавляет флаги _mediaHidden и _shouldHide
   */
  const applyFilters = (posts) => {
    return posts.map(post => ({
      ...post,
      _mediaHidden: shouldHideMedia(post),
      _shouldHide: shouldHidePost(post)
    }))
  }

  return {
    shouldHideMedia,
    shouldHidePost,
    applyFilters
  }
}
