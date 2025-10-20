<template>
  <div class="max-w-xl mx-auto print:max-w-none">
    <!-- Информация о канале -->
    <ChannelCover
      v-if="channelInfo"
      :channel="channelInfo"
      :postsCount="pagesCount"
      :commentsCount="0"
    />

    <!-- Книга страниц -->
    <Book
      :channelId="channelId"
      :pages="pages"
      :loading="pending"
    />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Book from '~/components/Book.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import { api } from '~/services/api'

const route = useRoute()
const channelId = route.params.channelId

const { data: pages, pending } = await useAsyncData(
  'pages',
  async () => {
    const response = await api.get(`/api/pages?channel_id=${channelId}`)
    return response.data
  }
)

const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

const pagesCount = computed(() => {
  return pages.value ? pages.value.length : 0
})
</script>