<template>
  <div class="post-with-comments">
    <!-- Оригинальный пост -->
    <Post 
      :post="originalPost" 
      :commentsCount="comments.length"
      :data-post-id="originalPost.telegram_id"
      :data-channel-id="originalPost.channel_id"
      class="original-post"
    />
    
    <!-- Комментарии -->
    <div v-if="comments.length > 0" class="comments-section  ml-8">
      <div class="comments-list">
        <Post 
          v-for="comment in sortedComments" 
          :key="`comment-${comment.id}`"
          :post="comment"
          :commentsCount="0"
          :data-post-id="comment.telegram_id"
          :data-channel-id="comment.channel_id"
          class="comment-post mb-4"
        />
      </div>
    </div>
  </div>
</template>

<script>
import Post from './Post.vue';

export default {
  name: "PostComments",
  components: { Post },
  props: {
    originalPost: { 
      type: Object, 
      required: true 
    },
    comments: { 
      type: Array, 
      default: () => [] 
    },
  },
  computed: {
    sortedComments() {
      // Сортируем комментарии по дате (старые сверху, как в обычных мессенджерах)
      return [...this.comments].sort((a, b) => new Date(a.date) - new Date(b.date));
    }
  }
};
</script>
