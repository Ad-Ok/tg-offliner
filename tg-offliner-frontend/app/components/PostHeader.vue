<template>
  <div class="post-header flex items-center justify-between gap-1 mb-2" :class="{ 'minimal:hidden': isOwner && isComment }">
    <PostAuthor
      :name="authorName"
      :avatar="authorAvatar"
      :link="authorLink"
      :class="{ 'minimal:hidden': isOwner }"
    />
    <span class="post-date ml-auto text-xs text-gray-400">{{ formattedDate }}</span>
  </div>
</template>

<script>
import PostAuthor from './PostAuthor.vue';
import { formatMessageDate } from '@/services/dateService';

export default {
  name: "PostHeader",
  props: {
    authorName: {
      type: String,
      required: true,
    },
    authorAvatar: {
      type: String,
      default: null,
    },
    authorLink: {
      type: String,
      default: null,
    },
    date: {
      type: String,
      required: true,
    },
    isOwner: {
      type: Boolean,
      default: false,
    },
    isComment: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    PostAuthor,
  },
  computed: {
    formattedDate() {
      return formatMessageDate(this.date);
    },
  },
};
</script>
