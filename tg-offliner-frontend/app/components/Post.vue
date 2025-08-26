<template>
  <div class="post w-full">
    <div class="post-wrap p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm">
      <PostHeader
        :author-name="post.author_name"
        :author-avatar="post.author_avatar"
        :author-link="post.author_link"
        :date="post.date"
      />

      <PostBody
        :original-post="originalPost"
        :message="post.message"
        :repost-author-name="post.repost_author_name"
        :repost-author-avatar="post.repost_author_avatar"
        :repost-author-link="post.repost_author_link"
      />

      <div v-if="post.media_url && post.media_type" class="mt-2 pl-11">
        <PostMedia
          :mediaUrl="post.media_url"
          :mediaType="post.media_type"
          :mimeType="post.mime_type"
        />
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
import PostBody from './PostBody.vue';

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
    PostBody,
  },
};
</script>
