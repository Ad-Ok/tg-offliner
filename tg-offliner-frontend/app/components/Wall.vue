<template>
  <div>
    <h1>Стена канала: {{ channelId }}</h1>
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else>

    </div>
  </div>
</template>

<script>
// import axios from 'axios';
import Post from './Post.vue';

export default {
  // eslint-disable-next-line vue/multi-word-component-names
  name: "Wall",
  components: {
    Post,
  },
  props: {
    channelId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      posts: [],
      loading: true,
    };
  },
  watch: {
    channelId: {
      immediate: true,
      handler(newChannelId) {
        this.fetchPosts(newChannelId);
      },
    },
  },
  // methods: {
  //   fetchPosts(channelId) {
  //     this.loading = true;
  //     axios
  //       .get(`http://127.0.0.1:5000/api/posts?channel_id=${channelId}`)
  //       .then((response) => {
  //         this.posts = response.data;
  //         this.loading = false;
  //       })
  //       .catch((error) => {
  //         console.error("Ошибка при загрузке постов:", error);
  //         this.loading = false;
  //       });
  //   },
  // },
};
</script>

<style>
.loading {
  font-size: 18px;
  text-align: center;
  margin-top: 20px;
}
</style>