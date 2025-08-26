<template>
  <div class="group w-full" :data-grouped-id="groupedId">
    <div class="p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm">
      <PostHeader
        :author-name="firstPost.author_name"
        :author-avatar="firstPost.author_avatar"
        :author-link="firstPost.author_link"
        :date="firstPost.date"
      />
      <PostBody
        :original-post="originalPost"
        :message="firstPost.message"
        :repost-author-name="firstPost.repost_author_name"
        :repost-author-avatar="firstPost.repost_author_avatar"
        :repost-author-link="firstPost.repost_author_link"
      />

      <div class="media-grid mt-2">
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
    </div>

    <PostFooter 
      :reactions="firstPost.reactions"
      :comments-count="0"
    />

  </div>
</template>

<script>
import PostHeader from './PostHeader.vue';
import PostMedia from './PostMedia.vue';
import PostFooter from './PostFooter.vue';
import PostBody from './PostBody.vue';

export default {
  name: "Group",
  props: {
    posts: {
      type: Array,
      required: true,
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
    PostBody,
  },
  computed: {
    firstPost() {
      return this.posts[0] || {};
    },
    groupedId() {
      return this.firstPost.grouped_id;
    },
    postsWithMedia() {
      return this.posts.filter(post => post.media_url && post.media_type);
    },
  },
};
</script>
