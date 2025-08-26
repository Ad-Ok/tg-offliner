<template>
  <div v-if="originalPost" class="post-quote bg-gray-50 dark:bg-gray-800 border-l-4 border-blue-500 p-3 mb-3 rounded">
    <div class="quote-header flex items-center space-x-2 mb-2">
      <img 
        v-if="originalPost.author_avatar" 
        :src="originalPost.author_avatar" 
        :alt="originalPost.author_name"
        class="w-6 h-6 rounded-full"
      />
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
        {{ originalPost.author_name }}
      </span>
      <span class="text-xs text-gray-500">
        {{ formatDate(originalPost.date) }}
      </span>
    </div>
    
    <div class="quote-content text-sm text-gray-600 dark:text-gray-400">
      <p v-if="originalPost.message" v-html="truncateMessage(originalPost.message)"></p>
      
      <!-- Превью медиа если есть -->
      <div v-if="originalPost.media_url" class="mt-2">
        <img 
          v-if="originalPost.media_type === 'photo'"
          :src="originalPost.media_url" 
          class="max-w-20 h-auto rounded"
        />
        <div v-else-if="originalPost.media_type === 'video'" class="flex items-center space-x-2">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 6a2 2 0 012-2h6l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"/>
          </svg>
          <span class="text-xs">Видео</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "PostQuote",
  props: {
    originalPost: {
      type: Object,
      default: null
    }
  },
  methods: {
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    
    truncateMessage(message) {
      if (!message) return '';
      // Убираем HTML теги для подсчета длины
      const textOnly = message.replace(/<[^>]*>/g, '');
      if (textOnly.length <= 100) return message;
      
      // Обрезаем по словам
      const truncated = textOnly.substring(0, 100);
      const lastSpace = truncated.lastIndexOf(' ');
      const result = lastSpace > 0 ? truncated.substring(0, lastSpace) : truncated;
      
      return result + '...';
    }
  }
};
</script>
