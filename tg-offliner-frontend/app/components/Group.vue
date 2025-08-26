<template>
  <div class="group w-full" :data-grouped-id="groupedId">
    <div class="p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm">
      <PostHeader
        :author-name="firstPost.author_name"
        :author-avatar="firstPost.author_avatar"
        :author-link="firstPost.author_link"
        :date="firstPost.date"
      />
      <div class="post-body pl-11">
        <div v-if="firstPost.repost_author_name" class="repost-author flex items-center space-x-4">
          <span class="text-sm text-gray-600 dark:text-gray-400">Репост от:</span>
          <PostAuthor
            :name="firstPost.repost_author_name"
            :avatar="firstPost.repost_author_avatar"
            :link="firstPost.repost_author_link"
          />
        </div>

        <p v-if="firstPost.message" v-html="firstPost.message"></p>
      </div>

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

    <div class="post-footer flex justify-between py-2 px-4 text-sm text-gray-500 dark:text-gray-400">
      <PostReactions v-if="firstPost.reactions" :reactions="firstPost.reactions" />
      <!-- <div v-if="commentsCount > 0" class="ml-auto">
        <span class="">
          {{ commentsCount }} {{ commentText }}
        </span>
      </div> -->
    </div>

  </div>
</template>

<script>
import PostHeader from './PostHeader.vue';
import PostAuthor from './PostAuthor.vue';
import PostMedia from './PostMedia.vue';
import PostReactions from './PostReactions.vue';

export default {
  name: "Group",
  props: {
    posts: {
      type: Array,
      required: true,
    },
  },
  components: {
    PostHeader,
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
    postsWithMedia() {
      return this.posts.filter(post => post.media_url && post.media_type);
    },
  },
};
</script>
