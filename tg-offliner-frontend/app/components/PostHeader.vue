<template>
  <div class="post-header flex items-center justify-between space-x-1 mb-2">
    <PostAuthor
      :name="authorName"
      :avatar="authorAvatar"
      :link="authorLink"
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
