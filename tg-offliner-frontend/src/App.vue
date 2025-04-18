<template>
  <div id="app">
    <h1>Лента постов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else>
      <div v-for="post in posts" :key="post.id" class="message">
        <!-- Дата сообщения -->
        <p><strong>Дата:</strong> {{ post.date }}</p>
        <!-- Текст сообщения -->
        <p v-html="post.message"></p>
        <!-- Медиа -->
        <div v-if="post.media_url">
          <p><strong>Медиа ({{ post.media_type }} - {{ post.mime_type }}):</strong></p>
          <div v-if="post.media_type === 'MessageMediaDocument'">
            <img v-if="post.mime_type && post.mime_type.startsWith('image/')" :src="post.media_url" alt="Медиа" />
            <video v-else-if="post.mime_type && post.mime_type.startsWith('video/')" controls>
              <source :src="post.media_url" />
            </video>
            <audio v-else-if="post.mime_type && post.mime_type.startsWith('audio/')" controls class="media">
                <source :src="post.media_url" :type="post.mime_type" />
                Ваш браузер не поддерживает аудио.
            </audio>
            <a v-else :href="post.media_url" target="_blank">Скачать файл</a>
          </div>
          <div v-else-if="post.media_type === 'MessageMediaPhoto'">
            <img :src="post.media_url" alt="Медиа" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      posts: [],
      loading: true,
    };
  },
  created() {
    // Загружаем посты с backend
    axios.get('http://127.0.0.1:5000/api/posts')
      .then(response => {
        this.posts = response.data;
        this.loading = false;
      })
      .catch(error => {
        console.error("Ошибка при загрузке постов:", error);
        this.loading = false;
      });
  },
};
</script>
