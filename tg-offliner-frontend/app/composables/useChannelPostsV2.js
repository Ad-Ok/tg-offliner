/**
 * useChannelPostsV2 composable
 * 
 * Единый composable для загрузки постов канала через API v2
 * Заменяет три разных пути загрузки в posts.vue
 * 
 * Приоритет параметров: URL > Saved > Default
 */

import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getChannelPosts, updateChannelSettings, setPostVisibility } from '~/services/apiV2'

/**
 * @typedef {import('~/services/apiV2').GetPostsResponse} GetPostsResponse
 * @typedef {import('~/services/apiV2').Post} Post
 * @typedef {import('~/services/apiV2').Channel} Channel
 * @typedef {import('~/services/apiV2').Pagination} Pagination
 * @typedef {import('~/services/apiV2').AppliedParams} AppliedParams
 */

/**
 * Composable для работы с постами канала через API v2
 * 
 * @param {string} channelId - ID канала
 * @returns {Object} - реактивные данные и методы
 */
export function useChannelPostsV2(channelId) {
  const route = useRoute()
  const router = useRouter()
  
  // === State ===
  
  /** @type {import('vue').Ref<Post[]>} */
  const posts = ref([])
  
  /** @type {import('vue').Ref<Channel|null>} */
  const channel = ref(null)
  
  /** @type {import('vue').Ref<Pagination|null>} */
  const pagination = ref(null)
  
  /** @type {import('vue').Ref<AppliedParams|null>} */
  const appliedParams = ref(null)
  
  /** @type {import('vue').Ref<boolean>} */
  const loading = ref(false)
  
  /** @type {import('vue').Ref<Error|null>} */
  const error = ref(null)
  
  // === Computed ===
  
  /**
   * Текущий chunk из URL или null (все посты)
   */
  const currentChunk = computed(() => {
    const chunk = route.query.chunk
    return chunk !== undefined ? parseInt(chunk, 10) : null
  })
  
  /**
   * Текущий sort_order: из applied_params (уже учитывает приоритет URL > Saved > Default)
   */
  const currentSortOrder = computed(() => {
    return appliedParams.value?.sort_order || 'desc'
  })
  
  /**
   * Источник текущего sort_order
   */
  const sortOrderSource = computed(() => {
    return appliedParams.value?.source || 'default'
  })
  
  /**
   * Есть ли следующий chunk
   */
  const hasNextChunk = computed(() => {
    return pagination.value?.has_next || false
  })
  
  /**
   * Есть ли предыдущий chunk
   */
  const hasPrevChunk = computed(() => {
    return pagination.value?.has_prev || false
  })
  
  /**
   * Общее количество постов (content units)
   */
  const totalPosts = computed(() => {
    return pagination.value?.total_posts || 0
  })
  
  /**
   * Общее количество комментариев
   */
  const totalComments = computed(() => {
    return pagination.value?.total_comments || 0
  })
  
  /**
   * Общее количество chunks
   */
  const totalChunks = computed(() => {
    return pagination.value?.total_chunks || 0
  })
  
  /**
   * Для совместимости со старым кодом
   */
  const channelInfo = computed(() => channel.value)
  
  /**
   * Для совместимости со старым кодом
   */
  const realPostsCount = computed(() => totalPosts.value)
  
  /**
   * Для совместимости со старым кодом
   */
  const totalCommentsCount = computed(() => totalComments.value)
  
  // === Methods ===
  
  /**
   * Загрузить посты с текущими параметрами из URL
   */
  async function fetchPosts() {
    loading.value = true
    error.value = null
    
    try {
      // Собираем опции из URL query
      const options = {}
      
      if (route.query.sort_order) {
        options.sortOrder = route.query.sort_order
      }
      
      if (route.query.chunk !== undefined) {
        options.chunk = parseInt(route.query.chunk, 10)
      }
      
      if (route.query.items_per_chunk) {
        options.itemsPerChunk = parseInt(route.query.items_per_chunk, 10)
      }
      
      // Всегда включаем комментарии
      options.includeComments = true
      
      console.log('[useChannelPostsV2] Fetching posts with options:', options)
      
      const response = await getChannelPosts(channelId, options)
      
      console.log('[useChannelPostsV2] Response applied_params:', response.applied_params)
      
      posts.value = response.posts
      channel.value = response.channel
      pagination.value = response.pagination
      appliedParams.value = response.applied_params
      
      return response
    } catch (e) {
      error.value = e
      console.error('[useChannelPostsV2] Error fetching posts:', e)
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Переключить sort_order
   * Меняет URL параметр (deferred save - не сохраняет автоматически)
   */
  function toggleSortOrder() {
    const newOrder = currentSortOrder.value === 'desc' ? 'asc' : 'desc'
    
    const query = { ...route.query }
    query.sort_order = newOrder
    
    // Сбрасываем chunk при смене сортировки
    delete query.chunk
    
    router.push({ query })
  }
  
  /**
   * Установить sort_order
   */
  function setSortOrder(order) {
    if (order !== 'asc' && order !== 'desc') return
    
    const query = { ...route.query }
    query.sort_order = order
    delete query.chunk
    
    router.push({ query })
  }
  
  /**
   * Сохранить текущие настройки на сервер
   */
  async function saveSettings() {
    if (!channel.value) return false
    
    try {
      const settings = {
        display: {
          sort_order: currentSortOrder.value
        }
      }
      
      await updateChannelSettings(channelId, settings)
      
      // Обновляем локальные данные
      if (channel.value.settings) {
        channel.value.settings.display = {
          ...channel.value.settings.display,
          ...settings.display
        }
      }
      
      console.log('[useChannelPostsV2] Settings saved')
      return true
    } catch (e) {
      console.error('[useChannelPostsV2] Error saving settings:', e)
      throw e
    }
  }
  
  /**
   * Сбросить URL параметры (использовать сохранённые настройки)
   */
  function resetToSaved() {
    const query = { ...route.query }
    delete query.sort_order
    delete query.chunk
    delete query.items_per_chunk
    
    router.push({ query })
  }
  
  /**
   * Перейти к chunk
   */
  function goToChunk(chunkNumber) {
    const query = { ...route.query }
    
    if (chunkNumber === null || chunkNumber === undefined) {
      delete query.chunk
    } else {
      query.chunk = String(chunkNumber)
    }
    
    router.push({ query })
  }
  
  /**
   * Следующий chunk
   */
  function nextChunk() {
    if (!hasNextChunk.value) return
    
    const current = currentChunk.value ?? 0
    goToChunk(current + 1)
  }
  
  /**
   * Предыдущий chunk
   */
  function prevChunk() {
    if (!hasPrevChunk.value) return
    
    const current = currentChunk.value ?? 0
    goToChunk(current > 0 ? current - 1 : null)
  }
  
  /**
   * Скрыть или показать пост
   */
  async function togglePostVisibility(telegramId, hidden) {
    try {
      await setPostVisibility(channelId, telegramId, hidden)
      
      // Обновляем локально
      const post = posts.value.find(p => p.telegram_id === telegramId)
      if (post) {
        post.is_hidden = hidden
      }
      
      return true
    } catch (e) {
      console.error('[useChannelPostsV2] Error toggling visibility:', e)
      throw e
    }
  }
  
  /**
   * Обновить layout поста
   */
  function updatePostLayout(groupedId, layout) {
    // Найти пост с этим grouped_id
    const post = posts.value.find(p => p.grouped_id === groupedId)
    if (post) {
      post.layout = layout
    }
  }
  
  /**
   * Перезагрузить посты
   */
  async function refresh() {
    return fetchPosts()
  }
  
  // Алиас для совместимости
  const load = fetchPosts
  
  // === Return ===
  
  return {
    // State
    posts,
    channel,
    channelInfo, // алиас для совместимости
    pagination,
    appliedParams,
    loading,
    error,
    
    // Computed
    currentChunk,
    currentSortOrder,
    sortOrderSource,
    hasNextChunk,
    hasPrevChunk,
    totalPosts,
    totalComments,
    totalChunks,
    realPostsCount, // алиас для совместимости
    totalCommentsCount, // алиас для совместимости
    
    // Methods
    fetchPosts,
    load, // алиас для совместимости
    refresh,
    toggleSortOrder,
    setSortOrder,
    saveSettings,
    resetToSaved,
    goToChunk,
    nextChunk,
    prevChunk,
    togglePostVisibility,
    updatePostLayout
  }
}

export default useChannelPostsV2
