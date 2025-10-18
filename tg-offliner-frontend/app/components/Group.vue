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

      <GroupEditor
        v-if="groupedId && firstPost.channel_id"
        :grouped-id="groupedId"
        :channel-id="firstPost.channel_id"
        @layoutReloaded="handleLayoutReloaded"
      />

      <div class="media-grid mt-2">
        <!-- Если есть layout, используем его для позиционирования -->
        <div v-show="layoutData" class="gallery-container relative" :style="galleryContainerStyle">
          <div
            v-for="(cell, index) in layoutData?.cells || []"
            :key="index"
            class="gallery-item absolute"
            :style="getCellStyle(cell)"
            v-show="cell.image_index < postsWithMedia.length && postsWithMedia[cell.image_index]"
          >
            <PostEditor :post="postsWithMedia[cell.image_index]" @hiddenStateChanged="(state) => onHiddenStateChanged(postsWithMedia[cell.image_index], state)"/>
            <PostMedia
              :mediaUrl="postsWithMedia[cell.image_index]?.thumb_url"
              :mediaType="postsWithMedia[cell.image_index]?.media_type"
              :mimeType="postsWithMedia[cell.image_index]?.mime_type"
              :class="[{ 'opacity-25 print:hidden': getPostHiddenState(postsWithMedia[cell.image_index]) && !editModeStore.isExportMode }, 'w-full h-full border']"
              :imgClass="'object-cover w-full h-full'"
            />
          </div>
        </div>
        <!-- Fallback: обычная grid -->
        <div v-show="!galleryLayout" class="grid grid-cols-2 gap-2">
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
import GroupEditor from './GroupEditor.vue';
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
    GroupEditor,
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
    
    const { data: layoutData, refresh: refreshLayout } = useFetch(() => {
      if (!props.posts.length || !props.posts[0]?.grouped_id) return null
      const groupedId = props.posts[0].grouped_id
      const channelId = props.posts[0].channel_id
      return `http://localhost:5000/api/layouts/${groupedId}?channel_id=${encodeURIComponent(channelId)}`
    }, {
      default: () => null,
      server: false, // Загружать только на клиенте
      onResponseError: ({ response }) => {
        console.warn('Failed to load gallery layout:', response?.status)
      }
    })
    
    const galleryContainerStyle = computed(() => {
      if (!layoutData.value) return {};
      return {
        width: `${layoutData.value.total_width}%`,
        paddingBottom: `${layoutData.value.total_height}%`
      };
    })
    const getCellStyle = (cell) => {
      if (!layoutData.value) return {}
      const totalWidth = layoutData.value.total_width
      const totalHeight = layoutData.value.total_height
      return {
        left: `${(cell.x / totalWidth * 100)}%`,
        top: `${(cell.y / totalHeight * 100)}%`,
        width: `${(cell.width / totalWidth * 100)}%`,
        height: `${(cell.height / totalHeight * 100)}%`
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

    const handleLayoutReloaded = async (newLayout) => {
      if (newLayout) {
        layoutData.value = newLayout
        return
      }

      if (typeof refreshLayout === 'function') {
        await refreshLayout()
      }
    }
    
    onMounted(async () => {
      editModeStore.checkAndSetExportMode()
    })
    
    return {
      editModeStore,
      layoutData,
      galleryContainerStyle,
      getPostHiddenState,
      onHiddenStateChanged,
      getCellStyle,
      handleLayoutReloaded
    }
  }
};
</script>
