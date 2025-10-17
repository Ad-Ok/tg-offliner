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
        <!-- Если есть layout, используем его для позиционирования -->
        <div v-if="galleryLayout" class="gallery-container relative" :style="galleryContainerStyle">
          <div
            v-for="(cell, index) in galleryLayout.cells"
            :key="index"
            class="gallery-item absolute"
            :style="getCellStyle(cell)"
          >
            <PostMedia
              :mediaUrl="post.thumb_url"
              :mediaType="post.media_type"
              :mimeType="post.mime_type"
              :class="{ 'opacity-25 print:hidden': getPostHiddenState(post) && !editModeStore.isExportMode }"
            />
          </div>
        </div>
        <!-- Fallback: обычная grid -->
        <div v-else class="grid grid-cols-2 gap-2">
          <div
            v-for="post in postsWithMedia"
            :key="post.id"
            class="media-item relative"
            :class="{ 'hidden': getPostHiddenState(post) && editModeStore.isExportMode }"
            :data-post-id="post.telegram_id"
          >
            <PostEditor :post="post" @hiddenStateChanged="(state) => onHiddenStateChanged(post, state)"/>
            <PostMedia
              :mediaUrl="post.thumb_url"
              :mediaType="post.media_type"
              :mimeType="post.mime_type"
              :class="{ 'opacity-25 print:hidden': getPostHiddenState(post) && !editModeStore.isExportMode }"
            />
          </div>
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
import { mediaBase } from '~/services/api'

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
      return this.posts
        .filter(post => post.media_url && post.media_type)
        .sort((a, b) => a.telegram_id - b.telegram_id);
    },
    galleryLayout() {
      return this.layoutData;
    },
    galleryContainerStyle() {
      if (!this.galleryLayout) return {};
      return {
        width: `${this.galleryLayout.total_width}px`,
        height: `${this.galleryLayout.total_height}px`
      };
    }
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
    
    // Загружаем layout для галереи
    const { data: layoutData } = useFetch(
      computed(() => {
        if (!props.posts.length || !props.posts[0].grouped_id) return null
        const groupedId = props.posts[0].grouped_id
        const channelId = props.posts[0].channel_id
        return `/downloads/${channelId}/layouts/gallery_${groupedId}.json`
      }),
      {
        default: () => null,
        server: false // Загружать только на клиенте
      }
    )
    
    // Получаем стиль для ячейки layout
    const getCellStyle = (cell) => {
      return {
        left: `${cell.x}px`,
        top: `${cell.y}px`,
        width: `${cell.width}px`,
        height: `${cell.height}px`
      }
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
    
    onMounted(async () => {
      editModeStore.checkAndSetExportMode()
    })
    
    return {
      editModeStore,
      layoutData,
      getPostHiddenState,
      onHiddenStateChanged,
      getCellStyle
    }
  }
};
</script>
