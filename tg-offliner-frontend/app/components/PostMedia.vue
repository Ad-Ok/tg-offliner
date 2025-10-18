<template>
  <div class="post-media" :data-media-type="mediaType" :data-mime-type="mimeType">
    <div v-if="mediaType === 'MessageMediaDocument'">
      <!-- Изображения -->
      <a
        v-if="mimeType && mimeType.startsWith('image/')"
        :href="fullMediaSrc"
        :data-fancybox="useFancybox ? 'channel-gallery' : null"
        :data-caption="caption"
      >
        <img
          :src="mediaSrc"
          alt="Медиа"
        />
      </a>
      <!-- Видео -->
      <a
        v-else-if="mimeType && mimeType.startsWith('video/')"
        :href="fullMediaSrc"
        :data-fancybox="useFancybox ? 'channel-gallery' : null"
        :data-caption="caption"
      >
        <video
          controls
        >
          <source :src="mediaSrc" />
        </video>
      </a>
      <audio
        v-else-if="mimeType && mimeType.startsWith('audio/')"
        controls
        class="media"
      >
        <source
          :src="mediaSrc"
          :type="mimeType"
        />
        Ваш браузер не поддерживает аудио.
      </audio>
      <a v-else :href="mediaSrc" target="_blank">Скачать файл</a>
    </div>
    <div v-else-if="mediaType === 'MessageMediaPhoto'" class="w-full h-full">
      <a
        :href="fullMediaSrc"
        :data-fancybox="useFancybox ? 'channel-gallery' : null"
        :data-caption="caption"
      >
        <img
          :src="mediaSrc"
          alt="Медиа"
          :class="imgClass"
        />
      </a>
    </div>
    <div v-else-if="mediaType === 'MessageMediaWebPage'">
      <div class="webpage-preview mt-2 border border-gray-200 bg-gray-100 rounded-lg px-4 py-2">
        <div class="flex justify-between align-baseline mb-1">
          <h4 class="text-sm font-semibold text-gray-500">Ссылка</h4>
          <p class="webpage-note text-xs text-gray-400 italic">Нажмите для открытия в новой вкладке</p>
        </div>
        <a 
          :href="mediaUrl" 
          target="_blank" 
          rel="noopener noreferrer"
          class="link link-primary"
        >
          {{ mediaUrl }}
        </a>
      </div>
    </div>
  </div>
</template>

<script>
import { mediaBase } from '~/services/api';

export default {
  name: "PostMedia",
  props: {
    mediaUrl: { type: String, required: true },
    mediaType: { type: String, required: true },
    mimeType: { type: String, required: false },
    imgClass: { type: String, required: false, default: 'w-full' },
    caption: { type: String, required: false, default: '' },
    fullMediaUrl: { type: String, required: false, default: '' },
    useFancybox: { type: Boolean, required: false, default: true }
  },
  computed: {
    mediaSrc() {
      // Для веб-страниц используем прямой URL без базового пути API
      if (this.mediaType === 'MessageMediaWebPage') {
        return this.mediaUrl;
      }
      // Для файлов используем базовый путь API
      return `${mediaBase}/downloads/${this.mediaUrl}`;
    },
    fullMediaSrc() {
      // Для fancybox используем полный размер если он есть
      if (this.fullMediaUrl) {
        return `${mediaBase}/downloads/${this.fullMediaUrl}`;
      }
      // Иначе используем обычный медиа URL
      return this.mediaSrc;
    }
  }
};
</script>
