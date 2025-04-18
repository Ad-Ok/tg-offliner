<template>
  <h1>Лента постов</h1>
  <div v-if="loading" class="loading">Загрузка...</div>
  <div v-else>
    <Post
      v-for="post in posts"
      :key="post.id"
      :post="post"
    />
  </div>
</template>

<script>
import axios from 'axios';
import Post from './components/Post.vue';

export default {
  components: {
    Post,
  },
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
.loading {
  font-size: 18px;
  text-align: center;
  margin-top: 20px;
}

.reactions {
  display: flex;
  margin-top: 10px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 5px;
}

.message {
  margin-bottom: 20px;
}
</style>
