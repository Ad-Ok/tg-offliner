<template>
  <div class="wall max-w-xl mx-auto">
    <!-- Информация о канале -->
    <ChannelCover 
      v-if="channelInfo" 
      :channel="channelInfo" 
      :postsCount="realPostsCount"
      :commentsCount="totalCommentsCount"
    />
    
    <!-- Кнопка переключения порядка сортировки -->
    <div v-if="!pending" class="mb-4 flex justify-end">
      <button 
        @click="toggleSortOrder"
        class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 rounded-lg flex items-center space-x-2 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path v-if="sortOrder === 'desc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"/>
        </svg>
        <span>{{ sortOrder === 'desc' ? 'Старые сначала' : 'Новые сначала' }}</span>
      </button>
    </div>
    
    <!-- Лента постов -->
    <Wall 
      :channelId="channelId" 
      :posts="posts" 
      :loading="pending"
      :sort-order="sortOrder"
      :discussion-group-id="channelInfo?.discussion_group_id ? String(channelInfo.discussion_group_id) : null"
    />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import { api } from '~/services/api'
import { useEditModeStore } from '~/stores/editMode'

const route = useRoute()
const channelId = route.params.channelId

// Состояние для сортировки постов
const sortOrder = ref('desc') // 'desc' = новые сверху, 'asc' = старые сверху

// Метод переключения порядка сортировки
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

const editModeStore = useEditModeStore()
editModeStore.checkAndSetExportMode()

const { data: posts, pending } = await useAsyncData(
  'posts',
  async () => {
    const mainPosts = await api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data);
    
    const channelInfo = await api.get(`/api/channels/${channelId}`).then(res => res.data);
    
    let allPosts = mainPosts;
    if (channelInfo?.discussion_group_id) {
      const discussionPosts = await api.get(`/api/posts?channel_id=${channelInfo.discussion_group_id}`).then(res => res.data);
      
      allPosts = [...mainPosts, ...discussionPosts];
      const uniquePosts = allPosts.filter((post, index, array) => 
        array.findIndex(p => p.id === post.id) === index
      );
      allPosts = uniquePosts;
    }
    
    try {
      const editsPromises = allPosts.map(async (post) => {
        try {
          const response = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`);
          const hiddenState = response.data?.edit?.changes?.hidden === 'true' || response.data?.edit?.changes?.hidden === true;
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: hiddenState };
        } catch (error) {
          return { postId: post.telegram_id, channelId: post.channel_id, hidden: false };
        }
      });
      
      const editsStates = await Promise.all(editsPromises);
      
      allPosts.forEach(post => {
        const editState = editsStates.find(e => e.postId === post.telegram_id && e.channelId === post.channel_id);
        post.isHidden = editState ? editState.hidden : false;
      });
      
    } catch (error) {
      console.error('Error loading hidden states:', error);
    }
    
    return allPosts;
  }
)

const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

const realPostsCount = computed(() => {
  if (!posts.value) return 0
  
  const mainPosts = posts.value.filter(post => !post.grouped_id && !post.reply_to)
  const groups = {}
  
  posts.value.forEach(post => {
    if (post.grouped_id && !post.reply_to) {
      groups[post.grouped_id] = true
    }
  })
  
  return mainPosts.length + Object.keys(groups).length
})

const totalCommentsCount = computed(() => {
  if (!posts.value) return 0
  return posts.value.filter(post => post.reply_to).length
})
</script>