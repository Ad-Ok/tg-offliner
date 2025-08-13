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
        <PostComments
          v-else-if="item.type === 'post-with-comments'"
          :originalPost="item.originalPost"
          :comments="item.comments"
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
import PostComments from './PostComments.vue';

export default {
  name: "Wall",
  components: { Post, Group, PostComments },
  props: {
    channelId: { type: String, required: true },
    posts: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
  computed: {
    filteredPosts() {
      // Исключаем посты с grouped_id и комментарии (посты с reply_to)
      return this.posts.filter(post => !post.grouped_id && !post.reply_to);
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
    postsWithComments() {
      // Группируем комментарии по reply_to
      const commentsMap = {};
      const originalPostsMap = {};
      
      // Сначала собираем все оригинальные посты и комментарии
      this.posts.forEach(post => {
        if (post.reply_to) {
          // Это комментарий
          const replyToId = post.reply_to;
          if (!commentsMap[replyToId]) {
            commentsMap[replyToId] = [];
          }
          commentsMap[replyToId].push(post);
        } else if (!post.grouped_id) {
          // Это оригинальный пост (не комментарий и не в группе)
          originalPostsMap[post.telegram_id] = post;
        }
      });
      
      // Создаем объекты для постов с комментариями
      const result = {};
      Object.keys(commentsMap).forEach(originalPostId => {
        const originalPost = originalPostsMap[originalPostId];
        if (originalPost) {
          result[originalPostId] = {
            originalPost,
            comments: commentsMap[originalPostId]
          };
        }
      });
      
      return result;
    },
    organizedPosts() {
      const result = [];
      
      // Добавляем посты с комментариями
      Object.entries(this.postsWithComments).forEach(([postId, data]) => {
        result.push({
          type: 'post-with-comments',
          key: `post-comments-${postId}`,
          originalPost: data.originalPost,
          comments: data.comments
        });
      });
      
      // Добавляем обычные посты (без комментариев)
      this.filteredPosts.forEach(post => {
        // Проверяем, что у этого поста нет комментариев
        if (!this.postsWithComments[post.telegram_id]) {
          result.push({
            type: 'post',
            key: `post-${post.id}`,
            post: post
          });
        }
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
        let dateA, dateB;
        
        if (a.type === 'post') {
          dateA = a.post.date;
        } else if (a.type === 'post-with-comments') {
          dateA = a.originalPost.date;
        } else if (a.type === 'group') {
          dateA = a.posts[0].date;
        }
        
        if (b.type === 'post') {
          dateB = b.post.date;
        } else if (b.type === 'post-with-comments') {
          dateB = b.originalPost.date;
        } else if (b.type === 'group') {
          dateB = b.posts[0].date;
        }
        
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
