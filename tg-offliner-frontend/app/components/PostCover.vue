<template>
  <div class="channel-cover bg-base-100 rounded-lg shadow-md mb-6 overflow-hidden">
    <!-- Header с аватаром и основной информацией -->
    <div class="cover-header bg-gradient-to-r from-primary to-secondary p-6 text-primary-content">
      <div class="flex items-center gap-4">
        <!-- Аватар канала -->
        <div class="avatar">
          <div class="w-20 h-20 rounded-full ring ring-primary-content ring-offset-base-100 ring-offset-2">
            <img 
              v-if="avatarSrc" 
              :src="avatarSrc" 
              :alt="channel.name"
              class="w-full h-full object-cover"
            />
            <div 
              v-else 
              class="w-full h-full bg-base-300 flex items-center justify-center text-2xl font-bold text-base-content"
            >
              {{ channelInitials }}
            </div>
          </div>
        </div>
        
        <!-- Название и базовая информация -->
        <div class="flex-1">
          <h1 class="text-3xl font-bold mb-2">{{ channel.name }}</h1>
          <div class="flex flex-wrap gap-4 text-sm opacity-90">
            <div v-if="channel.subscribers" class="flex items-center gap-1">
              <span>👥</span>
              <span>{{ formatSubscribers(channel.subscribers) }}</span>
            </div>
            <div v-if="channel.creation_date" class="flex items-center gap-1">
              <span>📅</span>
              <span>Создан {{ formatDate(channel.creation_date) }}</span>
            </div>
            <div class="flex items-center gap-1">
              <span>📝</span>
              <span>{{ postsCount }} {{ postsText }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Описание канала -->
    <div v-if="channel.description" class="cover-description p-6">
      <h3 class="text-lg font-semibold mb-3">О канале</h3>
      <p class="text-base-content/80 leading-relaxed">{{ channel.description }}</p>
    </div>
    
    <!-- Дополнительная информация -->
    <div class="cover-stats bg-base-200 p-4">
      <div class="flex flex-wrap gap-6 text-sm">
        <div class="stat-item">
          <span class="font-semibold">ID канала:</span>
          <span class="font-mono text-primary">{{ channel.id }}</span>
        </div>
        <div v-if="channel.discussion_group_id" class="stat-item">
          <span class="font-semibold">Группа обсуждений:</span>
          <span class="font-mono text-secondary">{{ channel.discussion_group_id }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { mediaBase } from '~/services/api';

const props = defineProps({
  channel: {
    type: Object,
    required: true
  },
  postsCount: {
    type: Number,
    default: 0
  }
});

// URL аватара с правильным базовым путем
const avatarSrc = computed(() => {
  return props.channel.avatar ? `${mediaBase}/downloads/${props.channel.avatar}` : null;
});

// Инициалы канала для случая, когда нет аватара
const channelInitials = computed(() => {
  if (!props.channel.name) return '?';
  return props.channel.name
    .split(' ')
    .map(word => word.charAt(0).toUpperCase())
    .join('')
    .substring(0, 2);
});

// Форматирование количества подписчиков
const formatSubscribers = (subscribers) => {
  const num = parseInt(subscribers);
  if (isNaN(num)) return subscribers;
  
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

// Форматирование даты
const formatDate = (dateString) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
};

// Правильное склонение слова "пост"
const postsText = computed(() => {
  const count = props.postsCount;
  if (count === 1) return 'пост';
  if (count >= 2 && count <= 4) return 'поста';
  return 'постов';
});
</script>
