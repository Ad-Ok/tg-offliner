<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 py-8">
    <div class="container mx-auto px-4">
      <!-- Header -->
      <div class="mb-8">
        <NuxtLink :to="`/preview/${channelId}`" class="btn btn-ghost mb-4">
          ← Back to Flow Preview
        </NuxtLink>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Frozen Layout Preview
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-2">
          Channel: {{ channelId }} • {{ frozenData?.pages_count || 0 }} pages
        </p>
      </div>

      <!-- Loading -->
      <div v-if="pending" class="flex justify-center items-center py-20">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-warning max-w-2xl mx-auto">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <h3 class="font-bold">No frozen layout found</h3>
          <div class="text-sm">
            Go to <NuxtLink :to="`/preview/${channelId}`" class="link link-primary">Flow Preview</NuxtLink> 
            and click "Freeze Layout" button first.
          </div>
        </div>
      </div>

      <!-- Pages -->
      <div v-if="!pending && !error">
        <div v-if="frozenData?.pages && frozenData.pages.length > 0" class="space-y-8">
          <div 
            v-for="page in frozenData.pages" 
            :key="page.page_number"
            class="frozen-page bg-white dark:bg-gray-800 shadow-lg mx-auto"
            :style="pageStyle"
          >
            <!-- Page number badge -->
            <div class="absolute -top-3 left-4 z-10 bg-blue-500 text-white px-3 py-1 rounded text-sm font-semibold">
              Page {{ page.page_number }}
            </div>

            <!-- Posts with absolute positioning -->
            <div 
              v-for="post in page.posts" 
              :key="`${post.channel_id}-${post.telegram_id}`"
              class="frozen-post absolute bg-white dark:bg-gray-800 overflow-hidden"
              :style="getPostStyle(post)"
            >
              <!-- Текст из базы Posts с HTML форматированием -->
              <div 
                v-if="getPostFromDb(post.telegram_id, post.channel_id)"
                class="post-body" 
              >
                <div 
                class="post-message text-sm text-gray-900 dark:text-gray-100" 
                v-html="getPostFromDb(post.telegram_id, post.channel_id).message"
                ></div>
              </div>
            </div>
            
            <!-- Media elements (images) with absolute positioning -->
            <template v-for="post in page.posts" :key="`media-${post.channel_id}-${post.telegram_id}`">
              <div
                v-for="(media, mediaIndex) in post.media"
                :key="`${post.channel_id}-${post.telegram_id}-media-${mediaIndex}`"
                class="frozen-media absolute"
                :style="getMediaStyle(media)"
              >
                <img
                  v-if="media.type === 'image'"
                  :src="getMediaUrl(media, post)"
                  class="w-full h-full object-cover"
                  alt="Post media"
                />
              </div>
            </template>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-20">
          <p class="text-gray-500 dark:text-gray-400 text-lg">
            No frozen layout available. Go to preview and click "Freeze Layout" first.
          </p>
          <NuxtLink :to="`/preview/${channelId}`" class="btn btn-primary mt-4">
            Go to Preview
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { api, mediaBase } from '~/services/api'

const route = useRoute()
const channelId = route.params.channelId

// Загрузка frozen layout
const { data: frozenData, pending, error } = await useAsyncData(
  `frozen-${channelId}`,
  () => api.get(`/api/pages/${channelId}/frozen`).then(res => res.data)
)

// Загрузка постов из базы для отображения текста
const { data: postsData } = await useAsyncData(
  `posts-${channelId}`,
  async () => {
    // Загружаем посты канала
    const mainPosts = await api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data)
    
    // Проверяем наличие discussion group
    const channelInfo = await api.get(`/api/channels/${channelId}`).then(res => res.data)
    
    let allPosts = mainPosts
    
    // Если есть discussion group, загружаем и его посты
    if (channelInfo?.discussion_group_id) {
      const discussionPosts = await api.get(`/api/posts?channel_id=${channelInfo.discussion_group_id}`).then(res => res.data)
      
      // Объединяем посты, удаляя дубликаты
      allPosts = [...mainPosts, ...discussionPosts]
      const uniquePosts = allPosts.filter((post, index, array) => 
        array.findIndex(p => p.id === post.id) === index
      )
      allPosts = uniquePosts
    }
    
    return allPosts
  }
)

// Создаем мапу постов для быстрого доступа
const postsMap = computed(() => {
  if (!postsData.value) return {}
  
  const map = {}
  postsData.value.forEach(post => {
    const key = `${post.channel_id}-${post.telegram_id}`
    map[key] = post
  })
  return map
})

// Функция для получения поста из базы
const getPostFromDb = (telegram_id, channel_id) => {
  const key = `${channel_id}-${telegram_id}`
  return postsMap.value[key]
}

// Стили для страницы (A4 по умолчанию)
const pageStyle = computed(() => ({
  width: '210mm',
  height: '297mm',
  position: 'relative',
  margin: '0 auto 2rem',
  padding: '20mm'
}))

// Стили для поста с абсолютным позиционированием
const getPostStyle = (post) => ({
  top: `${post.bounds.top}mm`,
  left: `${post.bounds.left}mm`,
  width: `${post.bounds.width}mm`,
  height: `${post.bounds.height}mm`,
  padding: '8px',
  border: '1px solid #e5e7eb'
})

// Стили для медиа элементов с абсолютным позиционированием
const getMediaStyle = (media) => {
  // Используем border_width из данных медиа (для галерей)
  const borderWidth = media.border_width || '0'
  const borderStyle = borderWidth !== '0' ? `${borderWidth}px solid white` : 'none'
  
  return {
    top: `${media.bounds.top}mm`,
    left: `${media.bounds.left}mm`,
    width: `${media.bounds.width}mm`,
    height: `${media.bounds.height}mm`,
    border: borderStyle
  }
}

// Функция для получения URL медиа файла
const getMediaUrl = (media, post) => {
  // Для галерей: media.telegram_id содержит ID отдельной картинки
  // Для одиночных изображений: используем post.telegram_id
  const telegram_id = media.telegram_id || post.telegram_id
  const channel_id = post.channel_id
  
  console.log(`getMediaUrl: telegram_id=${telegram_id} (media.telegram_id=${media.telegram_id}, post.telegram_id=${post.telegram_id}), channel_id=${channel_id}`)
  
  // Получаем пост с медиа из базы
  const mediaPost = getPostFromDb(telegram_id, channel_id)
  if (!mediaPost?.media_url) {
    console.warn(`getMediaUrl: media post not found for telegram_id=${telegram_id}, channel_id=${channel_id}`)
    return ''
  }
  
  const url = `${mediaBase}/downloads/${mediaPost.media_url}`
  console.log(`getMediaUrl: returning ${url}`)
  
  // media_url в базе: channel_id/media/file.jpg
  // Добавляем downloads/ и mediaBase
  return url
}
</script>

<style scoped>
.frozen-page {
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
}

.frozen-post {
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
}

.post-body :deep(strong) {
  font-weight: 600;
}

.post-body :deep(em) {
  font-style: italic;
}

.post-body :deep(code) {
  font-family: monospace;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.post-body :deep(a) {
  color: #3b82f6;
  text-decoration: underline;
}

/* Для печати */
@media print {
  .frozen-page {
    page-break-after: always;
    box-shadow: none;
    margin: 0;
  }
}
</style>
