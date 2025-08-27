<template>
  <div 
    class="post-container relative"
    :class="{ 'hidden': isHidden && editModeStore.isExportMode }"
  >
    <button 
      v-if="editModeStore.showDeleteButtons"
      @click="togglePostVisibility"
      :disabled="isSaving"
      :class="isHidden ? 'bg-gray-500 hover:bg-gray-600' : 'bg-red-500 hover:bg-red-600'"
      class="absolute top-2 right-2 z-10 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold cursor-pointer transition-colors shadow-lg print:hidden disabled:opacity-50 disabled:cursor-not-allowed"
      :title="isSaving ? 'Сохранение...' : (isHidden ? 'Показать пост' : 'Скрыть пост')"
    >
      <span v-if="isSaving">⏳</span>
      <span v-else-if="isHidden">👁</span>
      <span v-else>×</span>
    </button>
    
    <div 
      class="post w-full font-sans print:text-sm"
      :class="{ 'opacity-25 print:hidden': isHidden && !editModeStore.isExportMode }"
    >
      <div class="post-wrap p-4 bg-white dark:bg-black border tweet-border rounded-lg sm:rounded-lg overflow-hidden shadow-sm print:shadow-none print:border print:border-gray-300 print:p-3">
        <PostHeader
          :author-name="post.author_name"
          :author-avatar="post.author_avatar"
          :author-link="post.author_link"
          :date="post.date"
        />

        <PostBody
          :original-post="originalPost"
          :message="post.message"
          :repost-author-name="post.repost_author_name"
          :repost-author-avatar="post.repost_author_avatar"
          :repost-author-link="post.repost_author_link"
        />

        <div v-if="post.media_url && post.media_type" class="mt-2 pl-11">
          <PostMedia
            :mediaUrl="post.media_url"
            :mediaType="post.media_type"
            :mimeType="post.mime_type"
          />
        </div>
      </div>

      <PostFooter 
        :reactions="post.reactions"
        :comments-count="commentsCount"
      />
    </div>
  </div>
</template>

<script>
import PostHeader from './PostHeader.vue';
import PostMedia from './PostMedia.vue';
import PostFooter from './PostFooter.vue';
import PostBody from './PostBody.vue';
import { useEditModeStore } from '~/stores/editMode'

export default {
  // eslint-disable-next-line vue/multi-word-component-names
  name: "Post",
  props: {
    post: {
      type: Object,
      required: true,
    },
    commentsCount: {
      type: Number,
      default: 0,
    },
    originalPost: {
      type: Object,
      default: null,
    },
  },
  components: {
    PostHeader,
    PostMedia,
    PostFooter,
    PostBody,
  },
  setup(props) {
    const editModeStore = useEditModeStore()
    
    const isHidden = ref(props.post.isHidden || false)
    const isSaving = ref(false)
    const isLoading = ref(false)
    
    const loadHiddenState = async () => {
      if (props.post.isHidden !== undefined) {
        return
      }
      
      try {
        isLoading.value = true
        
        const { editsService } = await import('~/services/editsService.js')
        
        const hiddenState = await editsService.getPostHiddenState(
          props.post.telegram_id,
          props.post.channel_id
        )
        
        isHidden.value = hiddenState
        
      } catch (error) {
        console.error('Error loading post hidden state:', error)
        
      } finally {
        isLoading.value = false
      }
    }
    
    const hidePost = async () => {
      isHidden.value = true
      await saveHiddenState(true)
    }
    
    const showPost = async () => {
      isHidden.value = false
      await saveHiddenState(false)
    }
    
    const togglePostVisibility = async () => {
      if (isSaving.value) return // Предотвращаем множественные клики
      
      if (isHidden.value) {
        await showPost()
      } else {
        await hidePost()
      }
    }
    
    const saveHiddenState = async (hidden) => {
      try {
        isSaving.value = true
        
        const { editsService } = await import('~/services/editsService.js')
        
        await editsService.setPostHidden(
          props.post.telegram_id,
          props.post.channel_id,
          hidden
        )
        
      } catch (error) {
        console.error('Error saving post visibility state:', error)
        isHidden.value = !hidden
        
        alert('Ошибка при сохранении изменений. Попробуйте еще раз.')
        
      } finally {
        isSaving.value = false
      }
    }
    
    onMounted(() => {
      loadHiddenState()
      editModeStore.checkAndSetExportMode()
    })
    
    return {
      editModeStore,
      isHidden,
      isSaving,
      isLoading,
      hidePost,
      showPost,
      togglePostVisibility
    }
  }
};
</script>
