<template>
  <ClientOnly v-if="loading">
    <div class="loading">Загрузка...</div>
  </ClientOnly>
  <div v-else>
    <div v-for="item in organizedPostsWithDiscussion" :key="item.key" class="mb-6">
      <!-- Группа -->
      <template v-if="item.type === 'group'">
        <Group 
          :posts="item.posts" 
          :original-post="item.originalPost"
          :comments-count="item.discussionComments ? item.discussionComments.length : 0"
          :data-post-id="item.posts[0].telegram_id"
          :data-channel-id="item.posts[0].channel_id"
        />
      </template>
      
      <!-- Обычный пост -->
      <template v-else>
        <Post
          :post="item.post"
          :original-post="item.originalPost"
          :data-post-id="item.post.telegram_id"
          :data-channel-id="item.post.channel_id"
          :comments-count="item.discussionComments ? item.discussionComments.length : 0"
        />
      </template>
      
      <!-- Дискуссия (общая для постов и групп) -->
      <div v-if="item.discussionComments && item.discussionComments.length > 0" class="ml-8 mt-4">
        <Wall
          :channel-id="String(discussionGroupId)"
          :posts="item.discussionComments"
          :loading="false"
          :sort-order="'asc'"
          :discussion-group-id="null"
        />
      </div>
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
    discussionGroupId: { type: String, default: null },
    sortOrder: { type: String, default: 'desc' }, // 'desc' = новые сверху, 'asc' = старые сверху
  },
  computed: {
    // Основные посты (логика зависит от наличия discussionGroupId)
    mainPosts() {
      if (this.discussionGroupId) {
        const discussionGroupIdStr = String(this.discussionGroupId);
        // Если есть дискуссионная группа - показываем только основные посты (исключаем комментарии из дискуссионной группы)
        return this.posts.filter(post => 
          !post.grouped_id && 
          post.channel_id !== discussionGroupIdStr // Исключаем все посты из дискуссионной группы
        );
      } else {
        // Если нет дискуссионной группы - показываем все посты кроме сгруппированных (включая комментарии)
        return this.posts.filter(post => !post.grouped_id);
      }
    },
    
    // Группы постов
    groupedPosts() {
      const groups = {};
      const discussionGroupIdStr = this.discussionGroupId ? String(this.discussionGroupId) : null;
      
      this.posts.forEach(post => {
        if (post.grouped_id) {
          // Если это группа из дискуссионной группы (комментарий), пропускаем её
          // Она будет показана как комментарий к родительскому посту
          if (discussionGroupIdStr && post.channel_id === discussionGroupIdStr && post.reply_to) {
            return;
          }
          
          if (!groups[post.grouped_id]) {
            groups[post.grouped_id] = [];
          }
          groups[post.grouped_id].push(post);
        }
      });
      return groups;
    },
    
    // Карта постов для быстрого поиска по telegram_id
    postsMap() {
      const map = {};
      this.posts.forEach(post => {
        map[post.telegram_id] = post;
      });
      return map;
    },
    
    // Карта постов дискуссионной группы
    discussionPostsMap() {
      if (!this.discussionGroupId) return {};
      
      const discussionGroupIdStr = String(this.discussionGroupId);
      const map = {};
      this.posts.forEach(post => {
        if (post.channel_id === discussionGroupIdStr) {
          map[post.telegram_id] = post;
        }
      });
      return map;
    },
    
    // Организованные посты для отображения
    organizedPosts() {
      const result = [];
      
      // Добавляем обычные посты
      this.mainPosts.forEach(post => {
        const originalPost = post.reply_to ? this.postsMap[post.reply_to] : null;
        
        result.push({
          type: 'post',
          key: `post-${post.id}`,
          post: post,
          date: post.date,
          originalPost: originalPost
        });
      });
      
      // Добавляем группы
      Object.entries(this.groupedPosts).forEach(([groupId, posts]) => {
        const sortedPosts = posts.sort((a, b) => a.telegram_id - b.telegram_id);
        const firstPost = sortedPosts[0];
        const originalPost = firstPost.reply_to ? this.postsMap[firstPost.reply_to] : null;
        
        result.push({
          type: 'group',
          key: `group-${groupId}`,
          posts: sortedPosts,
          date: firstPost.date,
          originalPost: originalPost
        });
      });
      
      // Сортируем все по дате с учетом sortOrder
      return result.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return this.sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
      });
    },
    
    // Посты с комментариями из дискуссионной группы
    organizedPostsWithDiscussion() {
      if (!this.discussionGroupId) {
        return this.organizedPosts;
      }

      // Приводим discussionGroupId к строке для корректного сравнения
      const discussionGroupIdStr = String(this.discussionGroupId);

      return this.organizedPosts.map(item => {
        // Определяем telegram_id поста для поиска комментариев
        const targetPostId = item.type === 'group' ? item.posts[0].telegram_id : item.post.telegram_id;
        
        // Ищем комментарии среди ВСЕХ постов по channel_id и reply_to
        const discussionComments = this.posts.filter(post => {
          const channelMatch = post.channel_id === discussionGroupIdStr;
          const replyMatch = post.reply_to === targetPostId;
          return channelMatch && replyMatch;
        });
        
        return {
          ...item,
          discussionComments: discussionComments
        };
      });
    }
  }
};
</script>
