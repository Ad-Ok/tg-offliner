<template>
  <div class="post-media">
    <!-- <p class="debug"><strong>Медиа ({{ mediaType }} - {{ mimeType }}):</strong></p> -->
    <div v-if="mediaType === 'MessageMediaDocument'">
      <img
        v-if="mimeType && mimeType.startsWith('image/')"
        :src="mediaSrc"
        alt="Медиа"
      />
      <video
        v-else-if="mimeType && mimeType.startsWith('video/')"
        controls
      >
        <source :src="mediaSrc" />
      </video>
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
    <div v-else-if="mediaType === 'MessageMediaPhoto'">
      <img
        :src="mediaSrc"
        alt="Медиа"
      />
    </div>
    <div v-else-if="mediaType === 'MessageMediaWebPage'">
      <div class="webpage-preview">
        <h4>🔗 Ссылка</h4>
        <a 
          :href="mediaUrl" 
          target="_blank" 
          rel="noopener noreferrer"
          class="webpage-link"
        >
          {{ mediaUrl }}
        </a>
        <p class="webpage-note">Нажмите для открытия в новой вкладке</p>
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
  },
  computed: {
    mediaSrc() {
      // Для веб-страниц используем прямой URL без базового пути API
      if (this.mediaType === 'MessageMediaWebPage') {
        return this.mediaUrl;
      }
      // Для файлов используем базовый путь API
      return `${mediaBase}/downloads/${this.mediaUrl}`;
    }
  }
};
</script>

<style scoped>
.webpage-preview {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  background-color: #f9f9f9;
}

.webpage-preview h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 14px;
}

.webpage-link {
  display: block;
  color: #1976d2;
  text-decoration: none;
  word-break: break-all;
  margin-bottom: 4px;
  font-weight: 500;
}

.webpage-link:hover {
  text-decoration: underline;
}

.webpage-note {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #666;
  font-style: italic;
}
</style>