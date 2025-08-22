<template>
  <div class="group">
    <div class="group-header">
      <PostAuthor
        :name="firstPost.author_name"
        :avatar="firstPost.author_avatar"
        :link="firstPost.author_link"
      />
      <div class="post-meta">
        <span class="post-date">{{ formattedDate }}</span>
        <span class="grouped-id">Медиа-группа: {{ groupedId }}</span>
      </div>
    </div>

    <div v-if="firstPost.repost_author_name" class="repost-author">
      <span>Репост от:</span>
      <PostAuthor
        :name="firstPost.repost_author_name"
        :avatar="firstPost.repost_author_avatar"
        :link="firstPost.repost_author_link"
      />
    </div>

    <p v-if="firstPost.message" v-html="firstPost.message"></p>

    <div class="media-grid">
      <div
        v-for="post in postsWithMedia"
        :key="post.id"
        class="media-item"
      >
        <PostMedia
          :mediaUrl="post.media_url"
          :mediaType="post.media_type"
          :mimeType="post.mime_type"
        />
      </div>
    </div>

    <PostReactions v-if="firstPost.reactions" :reactions="firstPost.reactions" />
  </div>
</template>

<script>
import PostAuthor from './PostAuthor.vue';
import PostMedia from './PostMedia.vue';
import PostReactions from './PostReactions.vue';
import { formatMessageDate } from '@/services/dateService';

export default {
  name: "Group",
  props: {
    posts: {
      type: Array,
      required: true,
    },
  },
  components: {
    PostAuthor,
    PostMedia,
    PostReactions,
  },
  computed: {
    firstPost() {
      return this.posts[0] || {};
    },
    groupedId() {
      return this.firstPost.grouped_id;
    },
    formattedDate() {
      return formatMessageDate(this.firstPost.date);
    },
    postsWithMedia() {
      return this.posts.filter(post => post.media_url && post.media_type);
    },
  },
};
</script>

<style scoped>
.group {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background-color: #fff;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.post-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.grouped-id {
  font-size: 0.8em;
  color: #666;
  font-style: italic;
  margin-top: 2px;
}

.repost-author {
  margin-bottom: 12px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 0.9em;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin: 12px 0;
}

.media-item {
  border-radius: 4px;
  overflow: hidden;
}
</style>
