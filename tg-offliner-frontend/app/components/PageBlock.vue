<template>
  <div 
    class="page-block"
    :class="{
      'edit-mode': isEditMode,
      'view-mode': !isEditMode
    }"
  >
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
</template>

<script setup>
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
  }
})

const emit = defineEmits(['edit', 'delete'])

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
