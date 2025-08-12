<template>
  <div class="wall">
    <h1>Стена канала: {{ channelId }}</h1>
    <ClientOnly v-if="loading">
      <div class="loading">Загрузка...</div>
    </ClientOnly>
    <div v-else>
      <Post
        v-for="post in posts"
        :key="post.id"
        :post="post"
        :data-post-id="post.telegram_id"
        :data-channel-id="post.channel_id"
      />
    </div>
  </div>
</template>

<script>
import Post from './Post.vue';

export default {
  name: "Wall",
  components: { Post },
  props: {
    channelId: { type: String, required: true },
    posts: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
};
</script>
