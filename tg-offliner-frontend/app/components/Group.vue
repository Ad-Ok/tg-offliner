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
        :current-layout="layoutData"
        @layoutReloaded="handleLayoutReloaded"
        @borderUpdated="handleBorderUpdated"
      />

      <div class="media-grid mt-2">
        <!-- If there's a layout, use it for positioning -->
        <div v-show="layoutData" class="gallery-container relative" :style="galleryContainerStyle">
          <div
            v-for="(cell, index) in layoutData?.cells || []"
            :key="index"
            class="gallery-item absolute"
            :style="getCellStyle(cell)"
            v-show="cell && cell.image_index !== undefined && cell.image_index < postsWithMedia.length && postsWithMedia[cell.image_index]"
          >
            <PostEditor :post="postsWithMedia[cell.image_index]" @hiddenStateChanged="(state) => onHiddenStateChanged(postsWithMedia[cell.image_index], state)"/>
            <PostMedia
              :mediaUrl="postsWithMedia[cell.image_index]?.thumb_url"
              :fullMediaUrl="postsWithMedia[cell.image_index]?.media_url"
              :mediaType="postsWithMedia[cell.image_index]?.media_type"
              :mimeType="postsWithMedia[cell.image_index]?.mime_type"
              :isGallery="true"
              :class="[
                { 'opacity-25 print:hidden': getPostHiddenState(postsWithMedia[cell.image_index]) && !editModeStore.isExportMode }, 
                'w-full h-full border-transparent',
                borderClass
              ]"
              :imgClass="'object-cover w-full h-full'"
              :caption="getMediaCaption(postsWithMedia[cell.image_index])"
              :useFancybox="!!layoutData"
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
              :fullMediaUrl="post.media_url"
              :mediaType="post.media_type"
              :mimeType="post.mime_type"
              :isGallery="true"
              :class="{ 'opacity-25 print:hidden': getPostHiddenState(post) && !editModeStore.isExportMode }"
              :caption="getMediaCaption(post)"
              :useFancybox="!layoutData"
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
import PostEditor from './system/PostEditor.vue';
import GroupEditor from './system/GroupEditor.vue';
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
      // Find post with message text, fallback to first post
      const postWithMessage = this.posts.find(post => post.message && post.message.trim() !== '');
      return postWithMessage || this.posts[0] || {};
    },
    groupedId() {
      return (this.posts[0] || {}).grouped_id;
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
    
    const layoutData = ref(null)
    const groupedIdRef = computed(() => props.posts[0]?.grouped_id ?? null)
    const channelIdRef = computed(() => props.posts[0]?.channel_id ?? null)

    const syncLayoutFromProps = () => {
      const firstPost = props.posts[0]
      layoutData.value = firstPost?.layout || null
    }

    syncLayoutFromProps()

    watch(
      () => props.posts,
      () => {
        syncLayoutFromProps()
      },
      { deep: true }
    )

    const galleryContainerStyle = computed(() => {
      const layout = layoutData.value
      if (!layout) return {}
      return {
        width: `${layout.total_width}%`,
        paddingBottom: `${layout.total_height}%`
      }
    })

    const borderClass = computed(() => {
      const layout = layoutData.value
      if (!layout || !layout.border_width) return 'border-0'
      const borderWidth = layout.border_width
      // border-1 в Tailwind не существует, используем просто 'border'
      if (borderWidth === '1') return 'border'
      return `border-${borderWidth}`
    })

    const getCellStyle = (cell) => {
      const layout = layoutData.value
      if (!layout) return {}
      const totalWidth = layout.total_width
      const totalHeight = layout.total_height
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
    
    const getMediaCaption = (post) => {
      if (!post) return ''
      const parts = []
      if (post.author_name) {
        parts.push(post.author_name)
      }
      if (post.message) {
        parts.push(post.message)
      }
      return parts.join(' - ')
    }

  const handleLayoutReloaded = (newLayout) => {
      if (newLayout) {
        layoutData.value = newLayout
        props.posts.forEach(post => {
          if (post.grouped_id === groupedIdRef.value && post.channel_id === channelIdRef.value) {
            post.layout = newLayout
          }
        })
        return
      }

      layoutData.value = null
      props.posts.forEach(post => {
        if (post.grouped_id === groupedIdRef.value && post.channel_id === channelIdRef.value) {
          post.layout = null
        }
      })
    }

    const handleBorderUpdated = (newLayout) => {
      if (newLayout) {
        layoutData.value = newLayout
        props.posts.forEach(post => {
          if (post.grouped_id === groupedIdRef.value && post.channel_id === channelIdRef.value) {
            post.layout = newLayout
          }
        })
      }
    }
    
    onMounted(async () => {
      editModeStore.checkAndSetExportMode()
    })
    
    return {
      editModeStore,
      layoutData,
      galleryContainerStyle,
      borderClass,
      getPostHiddenState,
      onHiddenStateChanged,
      getCellStyle,
      handleLayoutReloaded,
      handleBorderUpdated,
      getMediaCaption
    }
  }
};
</script>
