<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 py-8">
    <div class="container mx-auto px-4">
      <!-- Header -->
      <div class="mb-8">
        <NuxtLink :to="`/preview/${channelId}`" class="btn btn-ghost mb-4">
          ← Back to Flow Preview
        </NuxtLink>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Frozen Layout Preview
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-2">
          Channel: {{ channelId }} • {{ frozenData?.pages_count || 0 }} pages
        </p>
      </div>

      <!-- Loading -->
      <div v-if="pending" class="flex justify-center items-center py-20">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-warning max-w-2xl mx-auto">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <h3 class="font-bold">No frozen layout found</h3>
          <div class="text-sm">
            Go to <NuxtLink :to="`/preview/${channelId}`" class="link link-primary">Flow Preview</NuxtLink> 
            and click "Freeze Layout" button first.
          </div>
        </div>
      </div>

      <!-- Pages -->
      <div v-if="!pending && !error">
        <div v-if="frozenData?.pages && frozenData.pages.length > 0" class="space-y-8">
          <div 
            v-for="page in frozenData.pages" 
            :key="page.page_number"
            class="frozen-page bg-white dark:bg-gray-800 shadow-lg mx-auto"
            :style="pageStyle"
          >
            <!-- Page number badge -->
            <div class="absolute -top-3 left-4 z-10 bg-blue-500 text-white px-3 py-1 rounded text-sm font-semibold">
              Page {{ page.page_number }}
            </div>

            <!-- Posts with absolute positioning -->
            <div 
              v-for="post in page.posts" 
              :key="`${post.channel_id}-${post.telegram_id}`"
              class="frozen-post absolute border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 p-2 rounded"
              :style="getPostStyle(post)"
            >
              <div class="text-xs font-mono text-gray-600 dark:text-gray-400 mb-1">
                {{ post.type }} #{{ post.telegram_id }}
              </div>
              <div class="text-xs text-gray-500 dark:text-gray-500">
                {{ post.bounds.width.toFixed(1) }}×{{ post.bounds.height.toFixed(1) }}mm
              </div>
              
              <!-- Elements preview -->
              <div v-if="post.elements && post.elements.length > 0" class="mt-2 text-xs text-gray-400">
                {{ post.elements.length }} element(s)
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-20">
          <p class="text-gray-500 dark:text-gray-400 text-lg">
            No frozen layout available. Go to preview and click "Freeze Layout" first.
          </p>
          <NuxtLink :to="`/preview/${channelId}`" class="btn btn-primary mt-4">
            Go to Preview
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { api } from '~/services/api'

const route = useRoute()
const channelId = route.params.channelId

// Загрузка frozen layout
const { data: frozenData, pending, error } = await useAsyncData(
  `frozen-${channelId}`,
  () => api.get(`/api/pages/${channelId}/frozen`).then(res => res.data)
)

// Стили для страницы (A4 по умолчанию)
const pageStyle = computed(() => ({
  width: '210mm',
  height: '297mm',
  position: 'relative',
  margin: '0 auto 2rem',
  padding: '20mm'
}))

// Стили для поста с абсолютным позиционированием
const getPostStyle = (post) => ({
  top: `${post.bounds.top}mm`,
  left: `${post.bounds.left}mm`,
  width: `${post.bounds.width}mm`,
  height: `${post.bounds.height}mm`
})
</script>

<style scoped>
.frozen-page {
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
}

.frozen-post {
  overflow: hidden;
}

/* Для печати */
@media print {
  .frozen-page {
    page-break-after: always;
    box-shadow: none;
    margin: 0;
  }
}
</style>
