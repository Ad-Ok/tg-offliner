<template>
  <div class="max-w-xl mx-auto print:max-w-none" :class="pageFormatClass">
    <!-- Информация о канале -->
    <ChannelCover 
      v-if="channelInfo" 
      :channel="channelInfo" 
      :postsCount="realPostsCount"
      :commentsCount="totalCommentsCount"
    />
    
    <!-- Навигация по chunks (только если больше 1 chunk) -->
    <ChunkNavigation
      v-if="chunksInfo"
      :chunksInfo="chunksInfo"
      v-model:currentChunk="currentChunk"
      :loading="chunkLoading"
      @chunkSelected="onChunkSelected"
    />
    
    <!-- Кнопка переключения порядка сортировки -->
    <div v-if="!pending && !chunkLoading" class="mb-4 flex justify-end print:hidden">
      <button 
        @click="toggleSortOrder"
        class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 rounded-lg flex items-center gap-2 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path v-if="sortOrder === 'desc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"/>
        </svg>
        <span>{{ sortOrder === 'desc' ? 'Старые сначала' : 'Новые сначала' }}</span>
      </button>
    </div>
    
    <!-- Лента постов -->
    <Wall 
      :channelId="channelId" 
      :posts="displayPosts" 
      :loading="pending || chunkLoading"
      :sort-order="sortOrder"
      :discussion-group-id="channelInfo?.discussion_group_id ? String(channelInfo.discussion_group_id) : null"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import ChunkNavigation from '~/components/ChunkNavigation.vue'
import { api } from '~/services/api'
import { getChannelChunks, getChunkPosts } from '~/services/chunksService'
import { useEditModeStore } from '~/stores/editMode'

const route = useRoute()
const channelId = route.params.channelId

// Читаем query параметры (для SSR/PDF экспорта)
const queryChunk = route.query.chunk !== undefined ? parseInt(String(route.query.chunk)) : null
const querySortOrder = route.query.sort_order ? String(route.query.sort_order) : null

// Состояние для сортировки постов
const sortOrder = ref(querySortOrder || 'desc')

// Состояние для chunks
const currentChunk = ref(queryChunk !== null ? queryChunk : 0) // из query или первый chunk по умолчанию
const chunkLoading = ref(false)
const chunkPosts = ref(null) // посты текущего chunk

const editModeStore = useEditModeStore()
editModeStore.checkAndSetExportMode()

// Метод переключения порядка сортировки
const toggleSortOrder = async () => {
  const newSortOrder = sortOrder.value === 'desc' ? 'asc' : 'desc'
  sortOrder.value = newSortOrder
  
  // Сбрасываем данные текущего chunk
  chunkPosts.value = null
  
  try {
    const currentChanges = channelInfo.value?.changes || {}
    const updatedChanges = {
      ...currentChanges,
      sortOrder: newSortOrder
    }
    
    await api.put(`/api/channels/${channelId}`, {
      changes: updatedChanges
    })
    
    if (channelInfo.value) {
      channelInfo.value.changes = updatedChanges
    }
    
    // Перезагружаем chunks с новой сортировкой
    await refreshChunksInfo()
    
    // Загружаем первый chunk с новой сортировкой
    if (currentChunk.value !== null && chunksInfo.value?.total_chunks > 0) {
      currentChunk.value = 0
      await onChunkSelected(0)
    }
    
    console.log(`Порядок сортировки изменен на: ${newSortOrder}`)
  } catch (error) {
    console.error('Ошибка при сохранении порядка сортировки:', error)
    sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  }
}

// Загружаем информацию о chunks
const { data: chunksInfo, refresh: refreshChunksInfo } = await useAsyncData(
  'chunksInfo',
  async () => {
    try {
      return await getChannelChunks(channelId, { sortOrder: sortOrder.value })
    } catch (error) {
      console.warn('Failed to load chunks info:', error)
      return null
    }
  }
)

// Если есть queryChunk - загружаем посты из chunk API (для SSR/PDF)
const { data: initialChunkPosts } = await useAsyncData(
  'initialChunkPosts',
  async () => {
    if (queryChunk === null) return null
    
    try {
      const response = await getChunkPosts(channelId, queryChunk, { sortOrder: sortOrder.value })
      
      // Объединяем посты и комментарии
      let posts = [...response.posts, ...response.comments]
      
      // Убираем дубликаты
      posts = posts.filter((post, index, array) =>
        array.findIndex(p => p.id === post.id) === index
      )
      
      return posts
    } catch (error) {
      console.warn('Failed to load chunk posts for SSR:', error)
      return null
    }
  }
)

// Инициализируем chunkPosts из SSR данных
if (initialChunkPosts.value) {
  chunkPosts.value = initialChunkPosts.value
}

// Загружаем все посты (для режима "Все" или если мало постов)
const { data: allPosts, pending } = await useAsyncData(
  'posts',
  async () => {
    // Если есть queryChunk - не загружаем все посты, они уже в initialChunkPosts
    if (queryChunk !== null) {
      return []
    }
    
    const mainPosts = await api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data)
    
    const channelInfoResp = await api.get(`/api/channels/${channelId}`).then(res => res.data)
    
    let allPosts = mainPosts
    if (channelInfoResp?.discussion_group_id) {
      const discussionPosts = await api.get(`/api/posts?channel_id=${channelInfoResp.discussion_group_id}`).then(res => res.data)
      
      allPosts = [...mainPosts, ...discussionPosts]
      const uniquePosts = allPosts.filter((post, index, array) =>
        array.findIndex(p => p.id === post.id) === index
      )
      allPosts = uniquePosts
    }
    
    // Загружаем состояния скрытия
    try {
      const editsPromises = allPosts.map(async (post) => {
        try {
          const response = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`)
          const hiddenState = response.data?.edit?.changes?.hidden === 'true' || response.data?.edit?.changes?.hidden === true
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: hiddenState }
        } catch (error) {
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: false }
        }
      })
      
      const editsStates = await Promise.all(editsPromises)
      
      allPosts.forEach(post => {
        const editState = editsStates.find(e => e.postId === post.telegram_id && e.channelId === post.channel_id)
        post.isHidden = editState ? editState.hidden : false
      })
      
    } catch (error) {
      console.error('Error loading hidden states:', error)
    }

    // Загружаем layouts для галерей
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
          } catch (error) {
            console.warn('Failed to preload layout for group', groupedId, 'channel', groupChannelId, error?.response?.data || error)
          }
        }))
      }
    } catch (error) {
      console.error('Error preloading gallery layouts:', error)
    }
    
    return allPosts
  }
)

// Загрузка информации о канале
const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

const router = useRouter()

// Обновление URL при изменении chunk (без перезагрузки страницы)
function updateUrlWithChunk(chunkIndex) {
  const query = { ...route.query }
  if (chunkIndex !== null) {
    query.chunk = String(chunkIndex)
    query.sort_order = sortOrder.value
  } else {
    delete query.chunk
    delete query.sort_order
  }
  router.replace({ query })
}

// Обработчик выбора chunk
async function onChunkSelected(chunkIndex) {
  if (chunkIndex === null) {
    // Показать все посты
    chunkPosts.value = null
    updateUrlWithChunk(null)
    return
  }
  
  chunkLoading.value = true
  try {
    const response = await getChunkPosts(channelId, chunkIndex, { sortOrder: sortOrder.value })
    
    // Объединяем посты и комментарии
    let posts = [...response.posts, ...response.comments]
    
    // Убираем дубликаты
    posts = posts.filter((post, index, array) =>
      array.findIndex(p => p.id === post.id) === index
    )
    
    // Загружаем layouts для галерей в chunk
    const uniqueGroupKeys = new Map()
    posts.forEach(post => {
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
          const resp = await api.get(`/api/layouts/${groupedId}?channel_id=${encodeURIComponent(groupChannelId)}`)
          const layout = resp.data
          if (layout) {
            posts.forEach(post => {
              if (post.channel_id === groupChannelId && post.grouped_id === groupedId) {
                post.layout = layout
              }
            })
          }
        } catch (error) {
          // Layout not found - ok
        }
      }))
    }
    
    chunkPosts.value = posts
    updateUrlWithChunk(chunkIndex)
  } catch (error) {
    console.error('Error loading chunk posts:', error)
    chunkPosts.value = null
    currentChunk.value = null
  } finally {
    chunkLoading.value = false
  }
}

// Посты для отображения (chunk или все)
const displayPosts = computed(() => {
  if (currentChunk.value !== null && chunkPosts.value) {
    return chunkPosts.value
  }
  return allPosts.value || []
})

// Автозагрузка chunk при наличии chunks (только на клиенте, не при SSR с queryChunk)
watch(chunksInfo, (info) => {
  // Если данные уже загружены через SSR (queryChunk) - пропускаем
  if (queryChunk !== null && chunkPosts.value) return
  
  if (info && info.total_chunks > 1) {
    if (currentChunk.value !== null && currentChunk.value >= 0 && !chunkPosts.value) {
      // Загружаем текущий chunk (по умолчанию 0)
      onChunkSelected(currentChunk.value)
    }
  } else if (!info || info.total_chunks <= 1) {
    // Если только 1 chunk или нет chunks - показываем все
    currentChunk.value = null
  }
}, { immediate: true })

// Вычисляем класс формата страницы для CSS правил
const pageFormatClass = computed(() => {
  const pageSize = channelInfo.value?.print_settings?.page_size || 'A4'
  return `page-format-${pageSize.toLowerCase()}`
})

// Инициализируем sortOrder из настроек канала (только если не задан через query)
watch(channelInfo, (newChannelInfo) => {
  // Query параметр имеет приоритет
  if (querySortOrder) return
  
  if (newChannelInfo?.changes?.sortOrder) {
    sortOrder.value = newChannelInfo.changes.sortOrder
  }
}, { immediate: true })

const realPostsCount = computed(() => {
  // Используем данные из chunksInfo если есть
  if (chunksInfo.value) {
    return chunksInfo.value.total_posts
  }
  
  if (!allPosts.value) return 0
  
  const singlePosts = allPosts.value.filter(post => !post.grouped_id && !post.reply_to)
  
  const uniqueGroups = new Set()
  allPosts.value.forEach(post => {
    if (post.grouped_id && !post.reply_to) {
      uniqueGroups.add(post.grouped_id)
    }
  })
  
  return singlePosts.length + uniqueGroups.size
})

const totalCommentsCount = computed(() => {
  // Используем данные из chunksInfo если есть
  if (chunksInfo.value) {
    return chunksInfo.value.total_comments
  }
  
  if (!allPosts.value) return 0
  return allPosts.value.filter(post => post.reply_to).length
})
</script>
