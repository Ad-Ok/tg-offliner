<template>
  <div class="author flex items-center space-x-3 text-sm min-w-0">
    <div class="avatar-wrapper h-8 w-8 rounded-full object-cover flex-shrink-0 bg-gray-200">
      <img v-if="avatar" :src="avatarSrc" :alt="name" class="avatar-image h-full w-full rounded-full object-cover" />
    </div>
    <a v-if="link" :href="link" target="_blank" class="font-medium text-gray-900">{{ name }}</a>
    <span v-else class="font-medium text-gray-900">{{ name }}</span>
  </div>
</template>

<script>
import { mediaBase } from '~/services/api';

export default {
  name: "PostAuthor",
  props: {
    name: {
      type: String,
      required: true,
    },
    avatar: {
      type: String,
      required: false,
    },
    link: {
      type: String,
      required: false,
    },
  },
  computed: {
    avatarSrc() {
      return this.avatar ? `${mediaBase}/downloads/${this.avatar}` : null;
    }
  }
};
</script>
