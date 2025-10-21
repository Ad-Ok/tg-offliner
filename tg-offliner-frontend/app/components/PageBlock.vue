<template>
  <div 
    class="page-block h-full"
    :class="{
      'edit-mode': isEditMode,
      'view-mode': !isEditMode
    }"
  >
    <!-- Если есть channel_id и telegram_id, загружаем и показываем пост -->
    <div v-if="content?.channel_id && content?.telegram_id" class="h-full">
      <div v-if="loading" class="flex items-center justify-center h-full p-4">
        <p class="text-gray-500">Загрузка поста...</p>
      </div>
      
      <div v-else-if="error" class="flex items-center justify-center h-full p-4">
        <p class="text-red-500">Ошибка: {{ error }}</p>
      </div>
      
      <div v-else-if="post" class="h-full overflow-auto">
        <Post :post="post" :comments-count="0" />
      </div>
      
      <div v-else class="flex items-center justify-center h-full p-4">
        <p class="text-gray-500">Пост не найден</p>
      </div>
    </div>

    <!-- Устаревший формат с title/description (для обратной совместимости) -->
    <div v-else>
      <!-- Заголовок блока -->
      <div v-if="content?.title" class="block-header">
        <h3 class="block-title">{{ content.title }}</h3>
        
        <!-- Кнопки управления блоком (только в режиме редактирования) -->
        <div v-if="isEditMode" class="block-controls">
          <button 
            @click="$emit('edit', blockId)"
            class="btn btn-xs btn-ghost"
            title="Редактировать контент"
          >
            ✏️
          </button>
          <button 
            @click="$emit('delete', blockId)"
            class="btn btn-xs btn-ghost text-error"
            title="Удалить блок"
          >
            🗑️
          </button>
        </div>
      </div>

      <!-- Основное содержимое блока -->
      <div class="block-content">
        <!-- Описание/текст -->
        <p v-if="content?.description" class="block-description">
          {{ content.description }}
        </p>

        <!-- Дополнительные поля контента -->
        <div v-if="content?.text" class="block-text" v-html="content.text"></div>
        
        <!-- Медиа контент (если есть) -->
        <div v-if="content?.media_url" class="block-media">
          <img 
            v-if="isImage(content.media_url)" 
            :src="content.media_url" 
            :alt="content.title || 'Изображение'"
            class="block-image"
          />
          <video 
            v-else-if="isVideo(content.media_url)"
            :src="content.media_url"
            controls
            class="block-video"
          />
          <a 
            v-else
            :href="content.media_url"
            target="_blank"
            class="block-link"
          >
            📎 {{ content.media_url }}
          </a>
        </div>

        <!-- Метаданные (в режиме редактирования) -->
        <div v-if="isEditMode && showMeta" class="block-meta">
          <span class="meta-badge">ID: {{ blockId }}</span>
          <span v-if="content?.type" class="meta-badge">Тип: {{ content.type }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import Post from './Post.vue'
import { api } from '~/services/api'

const props = defineProps({
  blockId: {
    type: String,
    required: true
  },
  content: {
    type: Object,
    default: () => ({})
  },
  isEditMode: {
    type: Boolean,
    default: false
  },
  showMeta: {
    type: Boolean,
    default: true
  },
  channelPosts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['edit', 'delete'])

// Состояние загрузки поста
const post = ref(null)
const loading = ref(false)
const error = ref(null)

// Если посты переданы через props, используем их
const postFromProps = computed(() => {
  if (!props.content?.telegram_id || !props.channelPosts.length) {
    return null
  }
  return props.channelPosts.find(p => p.telegram_id === props.content.telegram_id)
})

// Загрузка поста по channel_id и telegram_id (только если не передан через props)
const loadPost = async () => {
  // Если пост уже есть в props, используем его
  if (postFromProps.value) {
    post.value = postFromProps.value
    return
  }

  if (!props.content?.channel_id || !props.content?.telegram_id) {
    return
  }

  loading.value = true
  error.value = null
  post.value = null

  try {
    // Получаем все посты канала
    const response = await api.get(`/api/posts?channel_id=${props.content.channel_id}`)
    const posts = response.data
    
    // Находим нужный пост по telegram_id
    const foundPost = posts.find(p => p.telegram_id === props.content.telegram_id)
    
    if (foundPost) {
      post.value = foundPost
    } else {
      error.value = `Пост с ID ${props.content.telegram_id} не найден`
    }
  } catch (err) {
    console.error('Error loading post:', err)
    error.value = 'Ошибка загрузки поста'
  } finally {
    loading.value = false
  }
}

// Загружаем пост при монтировании компонента
onMounted(() => {
  loadPost()
})

// Перезагружаем пост при изменении content или channelPosts
watch([() => props.content, () => props.channelPosts], () => {
  loadPost()
}, { deep: true })

// Вспомогательные функции для определения типа медиа
const isImage = (url) => {
  if (!url) return false
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
  return imageExtensions.some(ext => url.toLowerCase().includes(ext))
}

const isVideo = (url) => {
  if (!url) return false
  const videoExtensions = ['.mp4', '.webm', '.ogg', '.mov']
  return videoExtensions.some(ext => url.toLowerCase().includes(ext))
}
</script>

<!-- Все стили теперь в tailwind.css -->
