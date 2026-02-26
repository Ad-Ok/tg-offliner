<template>
  <div class="min-h-screen bg-gray-100 py-8">
    <div class="container mx-auto px-4">
      <!-- Header -->
      <div class="mb-8">
        <NuxtLink :to="`/preview/${channelId}`" class="btn btn-ghost mb-4">
          ← Back to Flow Preview
        </NuxtLink>
        <h1 class="text-3xl font-bold text-gray-900">
          Frozen Layout Preview
        </h1>
        <p class="text-gray-600 mt-2">
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
            class="frozen-page bg-white shadow-lg mx-auto"
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
              class="frozen-post absolute bg-white overflow-hidden"
              :style="getPostStyle(post)"
            >
              <!-- Текст из базы Posts с HTML форматированием -->
              <div 
                v-if="getPostFromDb(post.telegram_id, post.channel_id)"
                class="post-body" 
              >
                <!-- Автор (аватар + имя) - только для комментариев от сторонних авторов -->
                <div v-if="shouldShowAuthor(post)" class="post-author flex items-center gap-2 mb-2">
                  <img 
                    v-if="getPostFromDb(post.telegram_id, post.channel_id)?.author_avatar" 
                    :src="getAuthorAvatarUrl(getPostFromDb(post.telegram_id, post.channel_id).author_avatar)"
                    class="author-avatar w-8 h-8 rounded-full object-cover"
                    alt="Author avatar"
                  />
                  <span class="author-name text-sm font-bold text-gray-900">{{ getPostFromDb(post.telegram_id, post.channel_id)?.author_name }}</span>
                </div>
                
                <!-- Дата поста (только для постов, не для комментариев) -->
                <div v-if="post.date && post.type !== 'comment'" class="post-date text-xs text-gray-400 mb-2">{{ post.date }}</div>
                
                <div 
                class="post-message text-gray-900" 
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
          <p class="text-gray-500 text-lg">
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
import { getChannelPosts } from '~/services/apiV2'
import { transformV2PostsToFlat } from '~/utils/v2Adapter'
import { PAGE_SIZES } from '~/utils/units'

const route = useRoute()
const channelId = route.params.channelId

// Загрузка постов и channel info через V2 API (один запрос)
const { data: v2Response } = await useAsyncData(
  `posts-${channelId}`,
  () => getChannelPosts(channelId, {
    includeHidden: true,
    includeComments: true,
  })
)

// Channel info из V2 response
const channelInfo = computed(() => v2Response.value?.channel || null)

// Посты в flat формате для отображения
const postsData = computed(() => {
  if (!v2Response.value?.posts) return []
  return transformV2PostsToFlat(
    v2Response.value.posts,
    v2Response.value.channel?.discussion_group_id
  )
})

// Загрузка frozen layout (V1 — нет V2 аналога для pages)
const { data: frozenData, pending, error } = await useAsyncData(
  `frozen-${channelId}`,
  () => api.get(`/api/pages/${channelId}/frozen`).then(res => res.data)
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

// Стили для страницы (динамические из print_settings канала)
const pageStyle = computed(() => {
  const exportSettings = channelInfo.value?.settings?.export
  const pageSizeKey = exportSettings?.page_size || 'A4'
  const pageSize = PAGE_SIZES[pageSizeKey] || PAGE_SIZES.A4
  const margins = exportSettings?.margins || [20, 20, 20, 20]

  return {
    width: `${pageSize.width}mm`,
    height: `${pageSize.height}mm`,
    position: 'relative',
    margin: '0 auto 2rem'
  }
})

// Top margin для вертикального смещения (bounds.top не включает верхнее поле,
// в отличие от bounds.left, который уже включает левое поле)
const topMargin = computed(() => {
  const exportSettings = channelInfo.value?.settings?.export
  const margins = exportSettings?.margins || [20, 20, 20, 20]
  return margins[0]
})

// Стили для поста с абсолютным позиционированием
const getPostStyle = (post) => ({
  top: `${post.bounds.top + topMargin.value}mm`,
  left: `${post.bounds.left}mm`,
  width: `${post.bounds.width}mm`,
  height: `${post.bounds.height}mm`,
  border: '1px solid #e5e7eb'
})

// Стили для медиа элементов с абсолютным позиционированием
const getMediaStyle = (media) => {
  // Используем border_width из данных медиа (для галерей)
  const borderWidth = media.border_width || '0'
  const borderStyle = borderWidth !== '0' ? `${borderWidth}px solid white` : 'none'
  
  return {
    top: `${media.bounds.top + topMargin.value}mm`,
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

// Функция для получения URL аватара автора
const getAuthorAvatarUrl = (avatarPath) => {
  return `${mediaBase}/downloads/${avatarPath}`
}

// Функция для определения нужно ли показывать автора (аватар + имя)
const shouldShowAuthor = (post) => {
  const dbPost = getPostFromDb(post.telegram_id, post.channel_id)
  if (!dbPost) return false
  
  // Это комментарий?
  const isComment = !!dbPost.reply_to
  if (!isComment) return false
  
  // Проверяем, не является ли автор владельцем канала или discussion group
  const authorLink = dbPost.author_link
  if (!authorLink) return false
  
  // Проверяем совпадение с каналом по username
  if (channelId && authorLink === `https://t.me/${channelId}`) {
    return false
  }
  
  // Проверяем совпадение с каналом по числовому ID (с префиксом channel_)
  if (channelId && channelId.startsWith('channel_')) {
    const numericId = channelId.replace('channel_', '')
    if (authorLink === `https://t.me/c/${numericId}`) {
      return false
    }
  }
  
  // Проверяем совпадение с каналом по чистому числовому ID (без префикса)
  if (channelId && /^\d+$/.test(channelId) && authorLink === `https://t.me/c/${channelId}`) {
    return false
  }
  
  // Проверяем совпадение с группой обсуждения
  if (channelInfo.value?.discussion_group_id && authorLink === `https://t.me/c/${channelInfo.value.discussion_group_id}`) {
    return false
  }
  
  return true
}
</script>


