<template>
  <div class="author">
    <img v-if="avatar" :src="avatarSrc" alt="Avatar" />
    <a v-if="link" :href="link" target="_blank">{{ name }}</a>
    <span v-else>{{ name }}</span>
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
