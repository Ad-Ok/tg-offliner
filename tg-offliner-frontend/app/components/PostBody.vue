<template>
  <div class="post-body pl-11">
    <!-- Цитата оригинального поста для комментариев -->
    <PostQuote 
      v-if="originalPost"
      :original-post="originalPost"
    />
    
    <!-- Информация о репосте -->
    <div v-if="repostAuthorName" class="repost-author flex items-center space-x-4">
      <span class="text-sm text-gray-600 dark:text-gray-400">Репост от:</span>
      <PostAuthor
        :name="repostAuthorName"
        :avatar="repostAuthorAvatar"
        :link="repostAuthorLink"
      />
    </div>

    <!-- Текст поста -->
    <p v-if="message" v-html="message"></p>
  </div>
</template>

<script>
import PostQuote from './PostQuote.vue';
import PostAuthor from './PostAuthor.vue';

export default {
  name: "PostBody",
  components: {
    PostQuote,
    PostAuthor
  },
  props: {
    originalPost: {
      type: Object,
      default: null
    },
    message: {
      type: String,
      default: null
    },
    repostAuthorName: {
      type: String,
      default: null
    },
    repostAuthorAvatar: {
      type: String,
      default: null
    },
    repostAuthorLink: {
      type: String,
      default: null
    }
  }
};
</script>
