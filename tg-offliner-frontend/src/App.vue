<template>
  <h1>Лента постов</h1>
  <div v-if="loading" class="loading">Загрузка...</div>
  <div v-else>
    <div v-for="post in posts" :key="post.id" class="message">
      <!-- Автор сообщения -->
      <PostAuthor
        :name="post.author_name"
        :avatar="post.author_avatar"
        :link="post.author_link"
      />

      <!-- Автор репоста -->
      <div v-if="post.repost_author_name" class="repost-author">
        <span>Репост от:</span>
        <PostAuthor
          :name="post.repost_author_name"
          :avatar="post.repost_author_avatar"
          :link="post.repost_author_link"
        />
      </div>
      <!-- Текст сообщения -->
      <p v-html="post.message"></p>
      <!-- Медиа -->
      <div v-if="post.media_url">
        <p><strong>Медиа ({{ post.media_type }} - {{ post.mime_type }}):</strong></p>
        <div v-if="post.media_type === 'MessageMediaDocument'">
          <img v-if="post.mime_type && post.mime_type.startsWith('image/')" :src="`http://127.0.0.1:5000/downloads/${post.media_url}`" alt="Медиа" />
          <video v-else-if="post.mime_type && post.mime_type.startsWith('video/')" controls>
            <source :src="`http://127.0.0.1:5000/downloads/${post.media_url}`" />
          </video>
          <audio v-else-if="post.mime_type && post.mime_type.startsWith('audio/')" controls class="media">
              <source :src="`http://127.0.0.1:5000/downloads/${post.media_url}`" :type="post.mime_type" />
              Ваш браузер не поддерживает аудио.
          </audio>
          <a v-else :href="post.media_url" target="_blank">Скачать файл</a>
        </div>
        <div v-else-if="post.media_type === 'MessageMediaPhoto'">
          <img :src="`http://127.0.0.1:5000/downloads/${post.media_url}`" alt="Медиа" />
        </div>
      </div>
      <!-- Реакции -->
      <div v-if="post.reactions" class="reactions">
        <div v-for="reaction in parsedReactions(post.reactions.recent_reactions)" :key="reaction.reaction" class="reaction">
          <span>{{ reaction.reaction }}</span> <span>{{ reaction.count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import PostAuthor from './components/PostAuthor.vue'; // Обновляем импорт

export default {
  components: {
    PostAuthor, // Обновляем имя компонента
  },
  data() {
    return {
      posts: [],
      loading: true,
    };
  },
  created() {
    // Загружаем посты с backend
    axios.get('http://127.0.0.1:5000/api/posts')
      .then(response => {
        this.posts = response.data;
        this.loading = false;
      })
      .catch(error => {
        console.error("Ошибка при загрузке постов:", error);
        this.loading = false;
      });
  },
  methods: {
    parsedReactions(reactions) {
      // Преобразуем реакции, чтобы извлечь только эмодзи
      return reactions.map(reaction => {
        const match = reaction.reaction.match(/emoticon='(.*?)'/); // Извлекаем значение из ReactionEmoji
        return {
          reaction: match ? match[1] : reaction.reaction, // Если найдено, берём эмодзи, иначе оставляем как есть
          count: reaction.count
        };
      });
    }
  }
};
</script>

<style>
.reactions {
  display: flex;
  margin-top: 10px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>
