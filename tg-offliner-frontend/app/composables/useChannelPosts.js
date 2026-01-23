/**
 * Composable для загрузки постов канала с поддержкой chunks
 */
import { ref, computed } from 'vue'
import { api } from '~/services/api'
import { getChunkPosts } from '~/services/chunksService'

/**
 * Загрузка постов канала с опциональной поддержкой chunk
 * @param {string} channelId - ID канала
 * @param {Object} options - Опции
 * @param {number|null} options.chunkIndex - Индекс chunk (null = все посты)
 * @param {Function} options.applyFilters - Функция применения фильтров
 */
export function useChannelPosts(channelId, options = {}) {
  const { chunkIndex = null, applyFilters = (posts) => posts } = options
  
  const posts = ref([])
  const channelInfo = ref(null)
  const chunksInfo = ref(null)
  const loading = ref(true)
  const error = ref(null)
  
  /**
   * Загружает hidden states для постов
   */
  async function loadHiddenStates(allPosts) {
    try {
      const editsPromises = allPosts.map(async (post) => {
        try {
          const response = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`)
          const hiddenState = response.data?.edit?.changes?.hidden === 'true' || 
                              response.data?.edit?.changes?.hidden === true
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: hiddenState }
        } catch (err) {
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: false }
        }
      })
      
      const editsStates = await Promise.all(editsPromises)
      
      allPosts.forEach(post => {
        const editState = editsStates.find(e => 
          e.postId === post.telegram_id && e.channelId === post.channel_id
        )
        post.isHidden = editState ? editState.hidden : false
      })
    } catch (err) {
      console.error('Error loading hidden states:', err)
    }
  }
  
  /**
   * Загружает layouts для галерей
   */
  async function loadGalleryLayouts(allPosts) {
    try {
      const uniqueGroupKeys = new Map()

      allPosts.forEach(post => {
        if (!post.grouped_id || post.media_type !== 'MessageMediaPhoto') {
          return
        }
        const key = `${post.channel_id}:${post.grouped_id}`
        if (!uniqueGroupKeys.has(key)) {
          uniqueGroupKeys.set(key, { channelId: post.channel_id, groupedId: post.grouped_id })
        }
      })

      if (uniqueGroupKeys.size) {
        await Promise.all(Array.from(uniqueGroupKeys.values()).map(async ({ channelId: groupChannelId, groupedId }) => {
          try {
            const response = await api.get(`/api/layouts/${groupedId}?channel_id=${encodeURIComponent(groupChannelId)}`)
            const layout = response.data
            if (layout) {
              allPosts.forEach(post => {
                if (post.channel_id === groupChannelId && post.grouped_id === groupedId) {
                  post.layout = layout
                }
              })
            }
          } catch (err) {
            console.warn('Failed to preload layout for group', groupedId, 'channel', groupChannelId)
          }
        }))
      }
    } catch (err) {
      console.error('Error preloading gallery layouts:', err)
    }
  }
  
  /**
   * Загружает все посты канала (включая дискуссионные)
   */
  async function loadAllPosts() {
    const mainPosts = await api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data)
    
    let allPosts = mainPosts
    if (channelInfo.value?.discussion_group_id) {
      const discussionPosts = await api.get(
        `/api/posts?channel_id=${channelInfo.value.discussion_group_id}`
      ).then(res => res.data)
      
      allPosts = [...mainPosts, ...discussionPosts]
      // Убираем дубликаты
      allPosts = allPosts.filter((post, index, array) =>
        array.findIndex(p => p.id === post.id) === index
      )
    }
    
    return allPosts
  }
  
  /**
   * Загружает посты из конкретного chunk
   */
  async function loadChunkPosts(index) {
    const response = await getChunkPosts(channelId, index)
    
    // Объединяем посты и комментарии
    let allPosts = [...response.posts, ...response.comments]
    
    // Убираем дубликаты
    allPosts = allPosts.filter((post, index, array) =>
      array.findIndex(p => p.id === post.id) === index
    )
    
    return allPosts
  }
  
  /**
   * Основная функция загрузки
   */
  async function load() {
    loading.value = true
    error.value = null
    
    try {
      // 1. Загружаем информацию о канале
      channelInfo.value = await api.get(`/api/channels/${channelId}`).then(res => res.data)
      
      // 2. Загружаем информацию о chunks
      try {
        chunksInfo.value = await api.get(`/api/chunks/${channelId}`).then(res => res.data)
      } catch (err) {
        console.warn('Failed to load chunks info:', err)
        chunksInfo.value = null
      }
      
      // 3. Загружаем посты (все или из chunk)
      let allPosts
      if (chunkIndex !== null && chunkIndex !== undefined) {
        allPosts = await loadChunkPosts(chunkIndex)
      } else {
        allPosts = await loadAllPosts()
      }
      
      // 4. Загружаем hidden states
      await loadHiddenStates(allPosts)
      
      // 5. Применяем фильтры
      allPosts = applyFilters(allPosts)
      
      // 6. Загружаем layouts для галерей
      await loadGalleryLayouts(allPosts)
      
      posts.value = allPosts
    } catch (err) {
      console.error('Error loading posts:', err)
      error.value = err
    } finally {
      loading.value = false
    }
  }
  
  // Computed свойства для статистики
  const realPostsCount = computed(() => {
    if (chunksInfo.value) {
      return chunksInfo.value.total_posts
    }
    
    if (!posts.value) return 0
    
    const singlePosts = posts.value.filter(post => !post.grouped_id && !post.reply_to)
    const uniqueGroups = new Set()
    posts.value.forEach(post => {
      if (post.grouped_id && !post.reply_to) {
        uniqueGroups.add(post.grouped_id)
      }
    })
    
    return singlePosts.length + uniqueGroups.size
  })
  
  const totalCommentsCount = computed(() => {
    if (chunksInfo.value) {
      return chunksInfo.value.total_comments
    }
    
    if (!posts.value) return 0
    return posts.value.filter(post => post.reply_to).length
  })
  
  return {
    posts,
    channelInfo,
    chunksInfo,
    loading,
    error,
    load,
    realPostsCount,
    totalCommentsCount
  }
}
