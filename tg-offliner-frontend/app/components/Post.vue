<template>
  <div class="post">
    <div class="post-header">
      <PostAuthor
        :name="post.author_name"
        :avatar="post.author_avatar"
        :link="post.author_link"
      />
      <span class="post-date">{{ formattedDate }}</span>
    </div>

    <div v-if="post.repost_author_name" class="repost-author">
      <span>Репост от:</span>
      <PostAuthor
        :name="post.repost_author_name"
        :avatar="post.repost_author_avatar"
        :link="post.repost_author_link"
      />
    </div>

    <p v-html="post.message"></p>

    <div v-if="post.media_url">
      <PostMedia
        :mediaUrl="post.media_url"
        :mediaType="post.media_type"
        :mimeType="post.mime_type"
      />
    </div>

    <PostReactions v-if="post.reactions" :reactions="post.reactions" />
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
  },
};
</script>

<style>
.post {
  margin-bottom: 20px;
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.post-date {
  font-size: 0.9em;
  color: #888;
}

.repost-author {
  margin-top: 10px;
  font-style: italic;
}
</style>