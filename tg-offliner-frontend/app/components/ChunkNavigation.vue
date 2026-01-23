<template>
  <div v-if="chunksInfo && chunksInfo.total_chunks > 1" class="chunk-navigation mb-4 print:hidden">
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-sm text-gray-500 dark:text-gray-400">
        Часть:
      </span>
      
      <!-- Кнопки chunks -->
      <div class="flex flex-wrap gap-1">
        <button
          v-for="chunk in chunksInfo.chunks"
          :key="chunk.index"
          @click="selectChunk(chunk.index)"
          :class="[
            'px-3 py-1 text-sm rounded-lg transition-colors',
            currentChunk === chunk.index
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300'
          ]"
          :title="formatChunkTooltip(chunk)"
        >
          {{ chunk.index + 1 }}
        </button>
        
        <!-- Кнопка "Все" -->
        <button
          @click="selectChunk(null)"
          :class="[
            'px-3 py-1 text-sm rounded-lg transition-colors',
            currentChunk === null
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300'
          ]"
          title="Показать все посты"
        >
          Все
        </button>
      </div>
      
      <!-- Информация о текущем chunk -->
      <span v-if="currentChunk !== null && currentChunkInfo" class="text-xs text-gray-400 dark:text-gray-500 ml-2">
        {{ formatChunkInfo(currentChunkInfo) }}
      </span>
      <span v-else-if="currentChunk === null" class="text-xs text-gray-400 dark:text-gray-500 ml-2">
        {{ chunksInfo.total_posts }} постов, {{ chunksInfo.total_comments }} комментариев
      </span>
    </div>
    
    <!-- Прогресс загрузки -->
    <div v-if="loading" class="mt-2">
      <div class="h-1 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
        <div class="h-full bg-blue-500 transition-all duration-300" :style="{ width: '100%' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  chunksInfo: {
    type: Object,
    default: null
  },
  currentChunk: {
    type: Number,
    default: null // null = все посты
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:currentChunk', 'chunkSelected'])

const currentChunkInfo = computed(() => {
  if (props.currentChunk === null || !props.chunksInfo?.chunks) return null
  return props.chunksInfo.chunks.find(c => c.index === props.currentChunk)
})

function selectChunk(index) {
  emit('update:currentChunk', index)
  emit('chunkSelected', index)
}

function formatChunkInfo(chunk) {
  const parts = []
  
  if (chunk.posts_count) {
    parts.push(`${chunk.posts_count} пост${getPostSuffix(chunk.posts_count)}`)
  }
  
  if (chunk.comments_count) {
    parts.push(`${chunk.comments_count} комм.`)
  }
  
  if (chunk.date_from && chunk.date_to) {
    if (chunk.date_from === chunk.date_to) {
      parts.push(formatDate(chunk.date_from))
    } else {
      parts.push(`${formatDate(chunk.date_from)} — ${formatDate(chunk.date_to)}`)
    }
  }
  
  return parts.join(' · ')
}

function formatChunkTooltip(chunk) {
  const lines = []
  lines.push(`Часть ${chunk.index + 1}`)
  lines.push(`${chunk.posts_count} постов`)
  if (chunk.comments_count) {
    lines.push(`${chunk.comments_count} комментариев`)
  }
  if (chunk.date_from && chunk.date_to) {
    lines.push(`${chunk.date_from} — ${chunk.date_to}`)
  }
  return lines.join('\n')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  // Простое форматирование даты (можно улучшить)
  const parts = dateStr.split('-')
  if (parts.length === 3) {
    return `${parts[2]}.${parts[1]}`
  }
  return dateStr
}

function getPostSuffix(count) {
  const lastDigit = count % 10
  const lastTwoDigits = count % 100
  
  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return 'ов'
  }
  if (lastDigit === 1) {
    return ''
  }
  if (lastDigit >= 2 && lastDigit <= 4) {
    return 'а'
  }
  return 'ов'
}
</script>