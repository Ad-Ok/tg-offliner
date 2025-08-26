<template>
  <div class="post w-full">
    <div class="post-wrap p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm">
      <PostHeader
        :author-name="post.author_name"
        :author-avatar="post.author_avatar"
        :author-link="post.author_link"
        :date="post.date"
      />

      <div class="post-body pl-11">
        <!-- Цитата оригинального поста для комментариев -->
        <PostQuote 
          v-if="originalPost"
          :original-post="originalPost"
        />
        
        <div v-if="post.repost_author_name" class="repost-author flex items-center space-x-4">
          <span class="text-sm text-gray-600 dark:text-gray-400">Репост от:</span>
          <PostAuthor
            :name="post.repost_author_name"
            :avatar="post.repost_author_avatar"
            :link="post.repost_author_link"
          />
        </div>
    
        <p v-html="post.message"></p>
    
        <div v-if="post.media_url && post.media_type" class="mt-2">
          <PostMedia
            :mediaUrl="post.media_url"
            :mediaType="post.media_type"
            :mimeType="post.mime_type"
          />
        </div>
      </div>
    </div>

    <PostFooter 
      :reactions="post.reactions"
      :comments-count="commentsCount"
    />
  </div>
</template>

<script>
import PostHeader from './PostHeader.vue';
import PostMedia from './PostMedia.vue';
import PostFooter from './PostFooter.vue';
import PostQuote from './PostQuote.vue';

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
    originalPost: {
      type: Object,
      default: null,
    },
  },
  components: {
    PostHeader,
    PostMedia,
    PostFooter,
    PostQuote,
  },
};
</script>
