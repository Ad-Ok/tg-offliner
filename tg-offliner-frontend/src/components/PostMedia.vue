
<template>
  <div class="post-media">
    <p><strong>Медиа ({{ mediaType }} - {{ mimeType }}):</strong></p>
    <div v-if="mediaType === 'MessageMediaDocument'">
      <img
        v-if="mimeType && mimeType.startsWith('image/')"
        :src="`http://127.0.0.1:5000/downloads/${mediaUrl}`"
        alt="Медиа"
      />
      <video
        v-else-if="mimeType && mimeType.startsWith('video/')"
        controls
      >
        <source :src="`http://127.0.0.1:5000/downloads/${mediaUrl}`" />
      </video>
      <audio
        v-else-if="mimeType && mimeType.startsWith('audio/')"
        controls
        class="media"
      >
        <source
          :src="`http://127.0.0.1:5000/downloads/${mediaUrl}`"
          :type="mimeType"
        />
        Ваш браузер не поддерживает аудио.
      </audio>
      <a v-else :href="`http://127.0.0.1:5000/downloads/${mediaUrl}`" target="_blank">Скачать файл</a>
    </div>
    <div v-else-if="mediaType === 'MessageMediaPhoto'">
      <img
        :src="`http://127.0.0.1:5000/downloads/${mediaUrl}`"
        alt="Медиа"
      />
    </div>
  </div>
</template>

<script>
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