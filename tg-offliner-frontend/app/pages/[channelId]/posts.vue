<template>
  <div class="wall max-w-xl mx-auto">
    <!-- Информация о канале -->
    <ChannelCover 
      v-if="channelInfo" 
      :channel="channelInfo" 
      :postsCount="realPostsCount"
      :commentsCount="totalCommentsCount"
    />
    
    <!-- Лента постов -->
    <Wall 
      :channelId="channelId" 
      :posts="posts" 
      :loading="pending"
      :discussion-group-id="channelInfo?.discussion_group_id"
    />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import { api } from '~/services/api'

const route = useRoute()
const channelId = route.params.channelId

const { data: posts, pending } = await useAsyncData(
  'posts',
  async () => {
    // Загружаем основные посты
    const mainPosts = await api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data);
    
    // Загружаем информацию о канале для получения discussion_group_id
    const channelInfo = await api.get(`/api/channels/${channelId}`).then(res => res.data);
    
    // Если есть дискуссионная группа, загружаем и её посты
    if (channelInfo?.discussion_group_id) {
      const discussionPosts = await api.get(`/api/posts?channel_id=${channelInfo.discussion_group_id}`).then(res => res.data);
      
      // Объединяем посты и убираем дубликаты по id
      const allPosts = [...mainPosts, ...discussionPosts];
      const uniquePosts = allPosts.filter((post, index, array) => 
        array.findIndex(p => p.id === post.id) === index
      );
      
      return uniquePosts;
    }
    
    return mainPosts;
  }
)

const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

// Подсчет реальных постов (основные посты + группы)
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

// Подсчет всех комментариев
const totalCommentsCount = computed(() => {
  if (!posts.value) return 0
  return posts.value.filter(post => post.reply_to).length
})
</script>