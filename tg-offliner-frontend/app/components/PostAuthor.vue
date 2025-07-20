<template>
  <div class="author">
    <img v-if="avatar" :src="avatarSrc" alt="Avatar" />
    <a v-if="link" :href="link" target="_blank">{{ name }}</a>
    <span v-else>{{ name }}</span>
  </div>
</template>

<script>
import { apiBase } from '~/services/api';

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
      return this.avatar ? `${apiBase}/downloads/${this.avatar}` : null;
    }
  }
};
</script>

<style>
.author {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.author img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 10px;
}

.author a {
  font-weight: bold;
  color: #007bff;
  text-decoration: none;
}

.author a:hover {
  text-decoration: underline;
}
</style>