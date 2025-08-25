<template>
  <div class="post w-full">
    <div class="post-wrap p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm">
      <div class="post-header flex items-center justify-between space-x-1 mb-2">
        <PostAuthor
          :name="post.author_name"
          :avatar="post.author_avatar"
          :link="post.author_link"
        />
        <span class="post-date ml-auto text-xs text-gray-400">{{ formattedDate }}</span>
      </div>

      <div class="post-body pl-11">
        <div v-if="post.repost_author_name" class="repost-author flex items-center space-x-4">
          <span class="text-sm text-gray-600 dark:text-gray-400">Репост от:</span>
          <PostAuthor
            :name="post.repost_author_name"
            :avatar="post.repost_author_avatar"
            :link="post.repost_author_link"
          />
        </div>
    
        <p v-html="post.message"></p>
    
        <div v-if="post.media_url && post.media_type">
          <PostMedia
            :mediaUrl="post.media_url"
            :mediaType="post.media_type"
            :mimeType="post.mime_type"
          />
        </div>
      </div>
    </div>

    <div class="post-footer flex justify-between py-2 px-4 text-sm text-gray-500 dark:text-gray-400">
      <PostReactions v-if="post.reactions" :reactions="post.reactions" />
      <div v-if="commentsCount > 0" class="ml-auto">
        <span class="">
          {{ commentsCount }} {{ commentText }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import PostAuthor from './PostAuthor.vue';
import PostMedia from './PostMedia.vue';
import PostReactions from './PostReactions.vue';
import { formatMessageDate } from '@/services/dateService'; // Импорт сервиса

export default {
  // eslint-disable-next-line vue/multi-word-component-names
  name: "Post",
  props: {
    post: {
      type: Object,
      required: true,
    },
    commentsCount: {
      type: Number,
      default: 0,
    },
  },
  components: {
    PostAuthor,
    PostMedia,
    PostReactions,
  },
  computed: {
    formattedDate() {
      return formatMessageDate(this.post.date);
    },
    commentText() {
      const count = this.commentsCount;
      if (count === 1) return 'комментарий';
      if (count >= 2 && count <= 4) return 'комментария';
      return 'комментариев';
    }
  },
};
</script>
