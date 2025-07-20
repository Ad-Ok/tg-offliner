<template>
  <div class="post-media">
    <p><strong>Медиа ({{ mediaType }} - {{ mimeType }}):</strong></p>
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
  </div>
</template>

<script>
import { apiBase } from '~/services/api';

export default {
  name: "PostMedia",
  props: {
    mediaUrl: {
      type: String,
      required: true,
    },
    mediaType: {
      type: String,
      required: true,
    },
    mimeType: {
      type: String,
      required: false,
    },
  },
  computed: {
    mediaSrc() {
      return `${apiBase}/downloads/${this.mediaUrl}`;
    }
  }
};
</script>

<style>
.post-media img {
  max-width: 100%;
  height: auto;
  margin-bottom: 10px;
}

.post-media video,
.post-media audio {
  max-width: 100%;
  margin-bottom: 10px;
}
</style>