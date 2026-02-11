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
      v-if="pagination && pagination.total_chunks > 1"
      :chunksInfo="chunksInfoCompat"
      v-model:currentChunk="localCurrentChunk"
      :loading="loading"
      @chunkSelected="onChunkSelected"
    />
    
    <!-- Кнопка переключения порядка сортировки -->
    <div v-if="!loading" class="mb-4 flex justify-between items-center print:hidden">
      <div class="text-xs text-gray-500">
        <span v-if="sortOrderSource === 'url'" class="text-blue-500">URL</span>
        <span v-else-if="sortOrderSource === 'saved'" class="text-green-500">Saved</span>
        <span v-else class="text-gray-400">Default</span>
      </div>
      <div class="flex gap-2">
        <button 
          v-if="sortOrderSource === 'url'"
          @click="handleSaveSettings"
          class="px-3 py-1 text-sm bg-green-100 hover:bg-green-200 dark:bg-green-800 dark:hover:bg-green-700 dark:text-green-200 rounded-lg flex items-center gap-2 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          <span>Сохранить</span>
        </button>
        <button 
          @click="toggleSortOrder"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 rounded-lg flex items-center gap-2 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="currentSortOrder === 'desc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"/>
          </svg>
          <span>{{ currentSortOrder === 'desc' ? 'Старые сначала' : 'Новые сначала' }}</span>
        </button>
      </div>
    </div>
    
    <!-- Лента постов -->
    <Wall 
      :channelId="channelId" 
      :posts="posts" 
      :loading="loading"
      :sort-order="currentSortOrder"
      :discussion-group-id="channelInfo?.discussion_group_id ? String(channelInfo.discussion_group_id) : null"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import ChunkNavigation from '~/components/ChunkNavigation.vue'
import { getChannelPosts, updateChannelSettings } from '~/services/apiV2'
import { useEditModeStore } from '~/stores/editMode'

const route = useRoute()
const router = useRouter()
const channelId = route.params.channelId

const editModeStore = useEditModeStore()
editModeStore.checkAndSetExportMode()

// === State ===
const posts = ref([])
const channel = ref(null)
const pagination = ref(null)
const appliedParams = ref(null)
const loading = ref(true)
const error = ref(null)

// Локальное состояние для ChunkNavigation
const localCurrentChunk = ref(0)

// === Computed ===

const channelInfo = computed(() => channel.value)

const currentSortOrder = computed(() => {
  return appliedParams.value?.sort_order || 'desc'
})

const sortOrderSource = computed(() => {
  return appliedParams.value?.source || 'default'
})

const realPostsCount = computed(() => {
  return pagination.value?.total_posts || 0
})

const totalCommentsCount = computed(() => {
  return pagination.value?.total_comments || 0
})

const pageFormatClass = computed(() => {
  const pageSize = channel.value?.settings?.export?.page_size || 'A4'
  return `page-format-${pageSize.toLowerCase()}`
})

// Совместимость с ChunkNavigation
const chunksInfoCompat = computed(() => {
  if (!pagination.value) return null
  return {
    total_chunks: pagination.value.total_chunks,
    total_posts: pagination.value.total_posts,
    total_comments: pagination.value.total_comments,
    items_per_chunk: pagination.value.items_per_chunk
  }
})

// === Methods ===

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
    
    console.log('[posts.vue v2] Fetching posts with options:', options)
    
    const response = await getChannelPosts(channelId, options)
    
    console.log('[posts.vue v2] Response applied_params:', response.applied_params)
    
    posts.value = response.posts
    channel.value = response.channel
    pagination.value = response.pagination
    appliedParams.value = response.applied_params
    
    // Синхронизируем локальный chunk
    localCurrentChunk.value = response.pagination.current_chunk ?? 0
    
  } catch (e) {
    error.value = e
    console.error('[posts.vue v2] Error fetching posts:', e)
  } finally {
    loading.value = false
  }
}

function toggleSortOrder() {
  const newOrder = currentSortOrder.value === 'desc' ? 'asc' : 'desc'
  
  const query = { ...route.query }
  query.sort_order = newOrder
  
  // Сбрасываем chunk при смене сортировки
  delete query.chunk
  
  router.push({ query })
}

async function handleSaveSettings() {
  try {
    await updateChannelSettings(channelId, {
      display: {
        sort_order: currentSortOrder.value
      }
    })
    
    // После сохранения - убираем URL параметр, чтобы использовать saved
    const query = { ...route.query }
    delete query.sort_order
    router.replace({ query })
    
    console.log('[posts.vue v2] Settings saved')
  } catch (e) {
    console.error('[posts.vue v2] Error saving settings:', e)
  }
}

function onChunkSelected(chunkIndex) {
  const query = { ...route.query }
  
  if (chunkIndex === null || chunkIndex === undefined) {
    delete query.chunk
  } else {
    query.chunk = String(chunkIndex)
  }
  
  router.push({ query })
}

// === SSR data loading ===

// Используем useAsyncData для SSR-совместимой начальной загрузки
const { data: initialData } = await useAsyncData(
  `posts-${channelId}`,
  async () => {
    const options = {
      includeComments: true
    }
    
    if (route.query.sort_order) {
      options.sortOrder = route.query.sort_order
    }
    
    if (route.query.chunk !== undefined) {
      options.chunk = parseInt(route.query.chunk, 10)
    }
    
    console.log('[posts.vue v2] SSR Fetching with options:', options)
    
    return getChannelPosts(channelId, options)
  }
)

// Инициализируем state из SSR данных
if (initialData.value) {
  posts.value = initialData.value.posts
  channel.value = initialData.value.channel
  pagination.value = initialData.value.pagination
  appliedParams.value = initialData.value.applied_params
  localCurrentChunk.value = initialData.value.pagination.current_chunk ?? 0
  loading.value = false
}

// === Watchers ===

// Перезагрузка при изменении URL параметров (на клиенте)
watch(
  () => [route.query.sort_order, route.query.chunk, route.query.items_per_chunk],
  () => {
    // Только на клиенте после гидратации
    if (import.meta.client) {
      fetchPosts()
    }
  }
)
</script>
