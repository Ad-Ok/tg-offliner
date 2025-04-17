<template>
  <div id="app">
    <h1>Лента постов</h1>
    <div v-if="loading">Загрузка...</div>
    <div v-else>
      <div v-for="post in posts" :key="post.id" class="post">
        <h2>{{ post.title }}</h2>
        <p>{{ post.content }}</p>
        <small>{{ post.date }}</small>
        <div v-if="post.media" class="media">
          <img :src="post.media" alt="Media" />
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

<style>
#app {
  font-family: Arial, sans-serif;
  margin: 20px;
}

.post {
  border: 1px solid #ddd;
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 5px;
}

.post h2 {
  margin: 0 0 10px;
}

.post small {
  color: #888;
}

.media img {
  max-width: 100%;
  height: auto;
  margin-top: 10px;
}
</style>
