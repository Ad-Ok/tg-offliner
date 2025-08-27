<template>
  <div class="group w-full" :data-grouped-id="groupedId">
    <div class="p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg shadow-sm">
      <PostHeader
        :author-name="firstPost.author_name"
        :author-avatar="firstPost.author_avatar"
        :author-link="firstPost.author_link"
        :date="firstPost.date"
      />
      <PostBody
        :original-post="originalPost"
        :message="firstPost.message"
        :repost-author-name="firstPost.repost_author_name"
        :repost-author-avatar="firstPost.repost_author_avatar"
        :repost-author-link="firstPost.repost_author_link"
      />

      <div class="media-grid mt-2">
        <div
          v-for="post in postsWithMedia"
          :key="post.id"
          class="media-item relative"
          :class="{ 'hidden': getPostHiddenState(post) && editModeStore.isExportMode }"
        >
          <PostEditor :post="post" @hiddenStateChanged="(state) => onHiddenStateChanged(post, state)"/>
          <PostMedia
            :mediaUrl="post.media_url"
            :mediaType="post.media_type"
            :mimeType="post.mime_type"
            :class="{ 'opacity-25 print:hidden': getPostHiddenState(post) && !editModeStore.isExportMode }"
          />
        </div>
      </div>
    </div>

    <PostFooter 
      :reactions="firstPost.reactions"
      :comments-count="commentsCount"
    />

  </div>
</template>

<script>
import PostHeader from './PostHeader.vue';
import PostMedia from './PostMedia.vue';
import PostFooter from './PostFooter.vue';
import PostBody from './PostBody.vue';
import PostEditor from './PostEditor.vue';
import { useEditModeStore } from '~/stores/editMode'

export default {
  name: "Group",
  props: {
    posts: {
      type: Array,
      required: true,
    },
    originalPost: {
      type: Object,
      default: null,
    },
    commentsCount: {
      type: Number,
      default: 0,
    },
  },
  components: {
    PostHeader,
    PostMedia,
    PostFooter,
    PostBody,
    PostEditor,
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
  setup(props) {
    const editModeStore = useEditModeStore()
    
    // Храним состояние скрытости для каждого поста в группе
    const hiddenStates = ref(new Map())
    
    // Инициализируем состояния для всех постов с медиа
    const initializeHiddenStates = () => {
      props.posts.forEach(post => {
        if (post.media_url && post.media_type) {
          const key = `${post.channel_id}:${post.telegram_id}`
          hiddenStates.value.set(key, post.isHidden || false)
        }
      })
    }
    
    // Инициализируем состояния сразу при создании компонента
    initializeHiddenStates()
    
    const getPostHiddenState = (post) => {
      const key = `${post.channel_id}:${post.telegram_id}`
      return hiddenStates.value.get(key) || false
    }
    
    const onHiddenStateChanged = (post, newHiddenState) => {
      const key = `${post.channel_id}:${post.telegram_id}`
      hiddenStates.value.set(key, newHiddenState)
    }
    
    onMounted(() => {
      editModeStore.checkAndSetExportMode()
    })
    
    return {
      editModeStore,
      getPostHiddenState,
      onHiddenStateChanged
    }
  }
};
</script>
