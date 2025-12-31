<template>
  <div class="post-footer flex justify-between py-2 px-4 text-sm text-gray-500 minimal:hidden">
    <PostReactions v-if="reactions" :reactions="reactions" />
    <div v-if="commentsCount > 0" class="ml-auto">
      <span class="">
        {{ commentsCount }} {{ commentText }}
      </span>
    </div>
  </div>
</template>

<script>
import PostReactions from './PostReactions.vue';

export default {
  name: "PostFooter",
  props: {
    reactions: {
      type: Object,
      default: null,
    },
    commentsCount: {
      type: Number,
      default: 0,
    },
  },
  components: {
    PostReactions,
  },
  computed: {
    commentText() {
      const count = this.commentsCount;
      if (count === 1) return 'комментарий';
      if (count >= 2 && count <= 4) return 'комментария';
      return 'комментариев';
    }
  },
};
</script>
