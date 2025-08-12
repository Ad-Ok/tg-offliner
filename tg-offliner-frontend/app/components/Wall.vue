<template>
  <div class="wall">
    <!-- Кнопка "назад" -->
    <div class="back-button-container">
      <button @click="goBack" class="back-button">
        <svg class="back-icon" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M12 19L5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Назад к списку каналов
      </button>
    </div>
    
    <h1>Стена канала: {{ channelId }}</h1>
    <ClientOnly v-if="loading">
      <div class="loading">Загрузка...</div>
    </ClientOnly>
    <div v-else>
      <template v-for="item in organizedPosts" :key="item.key">
        <Group
          v-if="item.type === 'group'"
          :posts="item.posts"
        />
        <Post
          v-else
          :post="item.post"
          :data-post-id="item.post.telegram_id"
          :data-channel-id="item.post.channel_id"
        />
      </template>
    </div>
  </div>
</template>

<script>
import Post from './Post.vue';
import Group from './Group.vue';

export default {
  name: "Wall",
  components: { Post, Group },
  props: {
    channelId: { type: String, required: true },
    posts: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
  computed: {
    filteredPosts() {
      return this.posts.filter(post => !post.grouped_id);
    },
    groupedPosts() {
      const groups = {};
      this.posts.forEach(post => {
        if (post.grouped_id) {
          if (!groups[post.grouped_id]) {
            groups[post.grouped_id] = [];
          }
          groups[post.grouped_id].push(post);
        }
      });
      return groups;
    },
    organizedPosts() {
      const result = [];
      
      // Добавляем обычные посты
      this.filteredPosts.forEach(post => {
        result.push({
          type: 'post',
          key: `post-${post.id}`,
          post: post
        });
      });
      
      // Добавляем группы
      Object.entries(this.groupedPosts).forEach(([groupId, posts]) => {
        result.push({
          type: 'group',
          key: `group-${groupId}`,
          posts: posts.sort((a, b) => a.telegram_id - b.telegram_id) // Сортируем по telegram_id
        });
      });
      
      // Сортируем все по дате (новые сверху)
      return result.sort((a, b) => {
        const dateA = a.type === 'post' ? a.post.date : a.posts[0].date;
        const dateB = b.type === 'post' ? b.post.date : b.posts[0].date;
        return new Date(dateB) - new Date(dateA);
      });
    },
  },
  methods: {
    goBack() {
      // Используем Vue Router для навигации назад
      this.$router.push('/');
    }
  }
};
</script>
