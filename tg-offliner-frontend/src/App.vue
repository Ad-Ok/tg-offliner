<template>
  <div id="app">
    <h1>Лента постов</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else>
      <div v-for="post in posts" :key="post.id" class="message">
        <!-- Дата сообщения -->
        <p><strong>Дата:</strong> {{ post.date }}</p>
        <!-- Текст сообщения с форматированием -->
        <p v-html="post.message"></p>
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
