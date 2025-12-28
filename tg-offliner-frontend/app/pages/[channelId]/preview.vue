<template>
  <div class="flex h-[calc(100vh-64px)]">
    <!-- Sidebar с настройками печати -->
    <PrintSettingsSidebar 
      ref="sidebarRef"
      :channel-id="channelId"
      :channel-info="channelInfo"
      :total-pages="totalPages"
    />
    
    <!-- Основная область с preview -->
    <div class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900" ref="previewContainer" :style="previewContainerStyle">
      <div class="mx-auto py-8" :class="pageFormatClass" style="width: var(--preview-width); padding-top: var(--preview-padding-top); padding-left: var(--preview-padding-left); padding-right: var(--preview-padding-right);">
        <!-- Информация о канале -->
        <ChannelCover 
          v-if="channelInfo" 
          :channel="channelInfo" 
          :postsCount="realPostsCount"
          :commentsCount="totalCommentsCount"
        />
        
        <!-- Лента постов в режиме preview с разрывами страниц -->
        <div ref="wallContainer">
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
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'
import ChannelCover from '~/components/ChannelCover.vue'
import PrintSettingsSidebar from '~/components/system/PrintSettingsSidebar.vue'
import { api } from '~/services/api'
import { PAGE_SIZES, mmToPx } from '~/utils/units'

const route = useRoute()
const channelId = route.params.channelId

// Refs
const sidebarRef = ref(null)
const wallContainer = ref(null)
const previewContainer = ref(null)
const totalPages = ref(0)
const pageBreaksData = ref([])

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
  
  // Считаем посты без групп и без ответов
  const singlePosts = posts.value.filter(post => !post.grouped_id && !post.reply_to)
  
  // Считаем уникальные группы (grouped_id) среди постов без ответов
  const uniqueGroups = new Set()
  posts.value.forEach(post => {
    if (post.grouped_id && !post.reply_to) {
      uniqueGroups.add(post.grouped_id)
    }
  })
  
  return singlePosts.length + uniqueGroups.size
})

const totalCommentsCount = computed(() => {
  if (!posts.value) return 0
  return posts.value.filter(post => post.reply_to).length
})

// Функция для создания визуального индикатора разрыва страницы
const createPageBreak = (pageNumber) => {
  const pageBreak = document.createElement('div')
  pageBreak.className = 'page-break border-t-4 border-dashed border-blue-400 my-8 relative'
  pageBreak.innerHTML = `
    <div class="absolute -top-6 left-0 bg-blue-500 text-white px-3 py-1 rounded text-xs font-semibold">
      Страница ${pageNumber}
    </div>
  `
  return pageBreak
}

// Computed стили для preview контейнера на основе настроек печати
const previewContainerStyle = computed(() => {
  if (!sidebarRef.value?.settings) return {}
  
  const settings = sidebarRef.value.settings
  const pageSize = PAGE_SIZES[settings.page_size] || PAGE_SIZES.A4
  const topMargin = settings.margins[0]
  const leftMargin = settings.margins[1]
  const bottomMargin = settings.margins[2]
  const rightMargin = settings.margins[3]
  
  return {
    '--preview-width': `${pageSize.width}mm`,
    '--preview-height': `${pageSize.height}mm`,
    '--preview-padding-top': `${topMargin}mm`,
    '--preview-padding-bottom': `${bottomMargin}mm`,
    '--preview-padding-left': `${leftMargin}mm`,
    '--preview-padding-right': `${rightMargin}mm`
  }
})

// Вычисляем класс формата страницы для CSS правил
const pageFormatClass = computed(() => {
  const settings = sidebarRef.value?.settings
  if (!settings) return 'page-format-a4'
  const pageSize = settings.page_size || 'A4'
  return `page-format-${pageSize.toLowerCase()}`
})

// Функция для вычисления разрывов страниц
const calculatePageBreaks = async () => {
  if (!wallContainer.value || !sidebarRef.value?.settings) return
  
  // Получаем настройки из sidebar
  const settings = sidebarRef.value.settings
  const pageSize = PAGE_SIZES[settings.page_size] || PAGE_SIZES.A4
  
  // Поля в миллиметрах
  const topMargin = settings.margins[0]
  const bottomMargin = settings.margins[2]
  
  // Высота контентной области страницы в пикселях
  const pageHeight = mmToPx(pageSize.height - topMargin - bottomMargin)
  
  // Находим все посты
  const posts = wallContainer.value.querySelectorAll('[data-post-id]')
  
  // Удаляем старые разрывы страниц и классы из всего контейнера
  const contentContainer = previewContainer.value?.querySelector('.mx-auto')
  if (contentContainer) {
    const oldBreaks = contentContainer.querySelectorAll('.page-break')
    oldBreaks.forEach(br => br.remove())
  }
  
  // Удаляем класс break-before-page со всех постов
  posts.forEach(post => {
    post.classList.remove('break-before-page')
  })
  
  let currentPageHeight = 0
  let pageCount = 1
  const pagesData = [{ page: 1, posts: [] }] // Структура: [{ page: 1, posts: [{telegram_id, channel_id}] }]
  
  // Учитываем высоту channel-cover в расчетах
  const channelCoverElement = previewContainer.value?.querySelector('.channel-cover')
  if (channelCoverElement) {
    currentPageHeight = channelCoverElement.offsetHeight
  }
  
  // Добавляем индикатор страницы 1 в самое начало (перед channel-cover)
  if (contentContainer && channelCoverElement) {
    contentContainer.insertBefore(createPageBreak(1), channelCoverElement)
  }
  
  posts.forEach((post, index) => {
    const postHeight = post.offsetHeight
    const postId = post.getAttribute('data-post-id')
    const postChannelId = post.getAttribute('data-channel-id')
    
    // Если добавление этого поста превысит высоту страницы
    if (currentPageHeight + postHeight > pageHeight && currentPageHeight > 0) {
      // Добавляем класс break-before-page к текущему посту (первому на новой странице)
      post.classList.add('break-before-page')
      
      // Вставляем визуальный индикатор разрыва страницы перед постом
      pageCount++
      post.parentNode.insertBefore(createPageBreak(pageCount), post)
      
      // Сбрасываем счетчик высоты
      currentPageHeight = postHeight
      pagesData.push({ page: pageCount, posts: [] })
    } else {
      currentPageHeight += postHeight
    }
    
    // Добавляем пост на текущую страницу
    if (postId && postChannelId) {
      pagesData[pagesData.length - 1].posts.push({
        telegram_id: parseInt(postId),
        channel_id: postChannelId
      })
    }
  })
  
  totalPages.value = pageCount
  pageBreaksData.value = pagesData
  
  // Сохраняем в базу данных для использования при экспорте
  await savePageBreaks(pagesData)
}

// Функция для сохранения информации о разрывах страниц
const savePageBreaks = async (pagesData) => {
  try {
    // Сохраняем в changes канала
    await api.put(`/api/channels/${channelId}`, {
      changes: {
        ...channelInfo.value?.changes,
        preview_pages: pagesData
      }
    })
    console.log('Page breaks saved:', pagesData.length, 'pages')
  } catch (error) {
    console.error('Error saving page breaks:', error)
  }
}

// Пересчитываем при монтировании
onMounted(() => {
  nextTick(() => {
    calculatePageBreaks()
  })
})

// Пересчитываем при изменении настроек печати
watch(() => sidebarRef.value?.settings, () => {
  nextTick(() => {
    calculatePageBreaks()
  })
}, { deep: true })
</script>
