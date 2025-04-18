
<template>
  <div class="author">
    <img
      v-if="avatar"
      :src="`http://127.0.0.1:5000/downloads/${avatar}`"
      alt="Avatar"
    />
    <a v-if="link" :href="link" target="_blank">{{ name }}</a>
    <span v-else>{{ name }}</span>
  </div>
</template>

<script>
export default {
  name: "PostAuthor", // Обновляем имя компонента
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