<template>
  <Wall 
    :channelId="channelId" 
    :posts="posts" 
    :channelInfo="channelInfo"
    :loading="pending" 
  />
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import { api } from '~/services/api'

const route = useRoute()
const channelId = route.params.channelId

const { data: posts, pending } = await useAsyncData(
  'posts',
  () => api.get(`/api/posts?channel_id=${channelId}`).then(res => res.data)
)

const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)
</script>