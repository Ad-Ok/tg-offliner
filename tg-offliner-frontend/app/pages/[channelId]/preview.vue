<template>
  <div class="flex h-[calc(100vh-64px)]">
    <!-- Sidebar с настройками печати -->
    <PrintSettingsSidebar 
      :channel-id="channelId"
      :channel-info="channelInfo"
      @export-pdf="handleExportPdf"
      @export-idml="handleExportIdml"
    />
    
    <!-- Основная область с preview -->
    <div class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
      <div class="max-w-4xl mx-auto py-8 px-4">
        <!-- Информация о канале -->
        <ChannelCover 
          v-if="channelInfo" 
          :channel="channelInfo" 
          :postsCount="realPostsCount"
          :commentsCount="totalCommentsCount"
        />
        
        <!-- Индикатор режима preview -->
        <div class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div class="flex items-center gap-2 text-blue-800 dark:text-blue-200">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            <span class="font-medium">Режим предпросмотра печати</span>
          </div>
          <p class="text-sm text-blue-700 dark:text-blue-300 mt-1">
            Настройте параметры в боковой панели, затем нажмите "Экспорт" для создания PDF или IDML файла
          </p>
        </div>
        
        <!-- Лента постов в режиме preview -->
        <Wall 
          :channelId="channelId" 
          :posts="posts" 
          :loading="pending"
          :sort-order="sortOrder"
          :discussion-group-id="channelInfo?.discussion_group_id ? String(channelInfo.discussion_group_id) : null"
          :mode="'preview'"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import PrintSettingsSidebar from '~/components/system/PrintSettingsSidebar.vue'
import { api, apiBase } from '~/services/api'
import { eventBus } from '~/eventBus'

const route = useRoute()
const channelId = route.params.channelId

// Состояние для сортировки постов
const sortOrder = ref('desc')

// Загрузка данных (копируем логику из posts.vue)
const { data: posts, pending } = await useAsyncData(
  'preview-posts',
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

    try {
      const uniqueGroupKeys = new Map()

      allPosts.forEach(post => {
        if (!post.grouped_id || post.media_type !== 'MessageMediaPhoto') {
          return
        }
        const key = `${post.channel_id}:${post.grouped_id}`
        if (!uniqueGroupKeys.has(key)) {
          uniqueGroupKeys.set(key, { channelId: post.channel_id, groupedId: post.grouped_id })
        }
      })

      if (uniqueGroupKeys.size) {
        await Promise.all(Array.from(uniqueGroupKeys.values()).map(async ({ channelId: groupChannelId, groupedId }) => {
          try {
            const response = await api.get(`/api/layouts/${groupedId}?channel_id=${encodeURIComponent(groupChannelId)}`)
            const layout = response.data
            if (layout) {
              allPosts.forEach(post => {
                if (post.channel_id === groupChannelId && post.grouped_id === groupedId) {
                  post.layout = layout
                }
              })
            }
          } catch (error) {
            console.warn('Failed to preload layout for group', groupedId, 'channel', groupChannelId, error?.response?.data || error)
          }
        }))
      }
    } catch (error) {
      console.error('Error preloading gallery layouts:', error)
    }
    
    return allPosts;
  }
)

const { data: channelInfo } = await useAsyncData(
  'preview-channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

// Инициализируем sortOrder из настроек канала
watch(channelInfo, (newChannelInfo) => {
  if (newChannelInfo?.changes?.sortOrder) {
    sortOrder.value = newChannelInfo.changes.sortOrder
  }
}, { immediate: true })

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

// Обработчики экспорта
const handleExportPdf = async () => {
  try {
    const res = await fetch(`${apiBase}/api/channels/${channelId}/print`)
    const contentType = res.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const result = await res.json()
      if (result.success) {
        const filePath = `downloads/${channelId}/${channelId}.pdf`
        const fileUrl = `http://localhost:5000/${filePath}`
        eventBus.showAlert(
          `PDF файл для канала <strong>${channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
          "success",
          { html: true }
        )
      } else {
        eventBus.showAlert(result.error || "Ошибка создания PDF", "danger")
      }
    }
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка создания PDF", "danger")
    console.error("Error creating PDF:", error)
  }
}

const handleExportIdml = async () => {
  try {
    const res = await fetch(`${apiBase}/api/channels/${channelId}/export-idml`)
    const contentType = res.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const result = await res.json()
      if (result.success) {
        const filePath = `downloads/${channelId}/${channelId}.idml`
        const fileUrl = `http://localhost:5000/${filePath}`
        eventBus.showAlert(
          `IDML файл для канала <strong>${channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
          "success",
          { html: true }
        )
      } else {
        eventBus.showAlert(result.error || "Ошибка создания IDML", "danger")
      }
    }
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка создания IDML", "danger")
    console.error("Error creating IDML:", error)
  }
}
</script>
