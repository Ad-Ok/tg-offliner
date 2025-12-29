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
      <div class="mx-auto" :class="pageFormatClass" style="width: var(--preview-width);  padding-left: var(--preview-padding-left); padding-right: var(--preview-padding-right);">
        <!-- Информация о канале - скрыто в preview -->
        <!-- <ChannelCover 
          v-if="channelInfo" 
          :channel="channelInfo" 
          :postsCount="realPostsCount"
          :commentsCount="totalCommentsCount"
        /> -->
        
        <!-- Лента постов в режиме preview с разрывами страниц -->
        <div ref="wallContainer">
          <Wall 
            :channelId="channelId" 
            :posts="posts" 
            :loading="pending"
            :sort-order="sortOrder"
            :discussion-group-id="channelInfo?.discussion_group_id ? String(channelInfo.discussion_group_id) : null"
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
import { PAGE_SIZES, mmToPx, pxToMm } from '~/utils/units'
import { useEditModeStore } from '~/stores/editMode'
import { usePostFiltering } from '~/composables/usePostFiltering'

const route = useRoute()
const channelId = route.params.channelId
const editModeStore = useEditModeStore()
const { applyFilters } = usePostFiltering()

// Refs
const sidebarRef = ref(null)
const wallContainer = ref(null)
const previewContainer = ref(null)
const totalPages = ref(0)
const pageBreaksData = ref([])

// Состояние для сортировки постов
const sortOrder = ref('desc')

// Режим редактирования - используем computed для связи со store
const isEditMode = computed(() => editModeStore.isPreviewEditMode)

// Функция пересчета страниц - экспортируем для вызова из Navbar
const recalculatePages = () => {
  calculatePageBreaks()
}

// TODO: Функция для freeze layout - извлечение координат из текущей пагинации
const freezeCurrentLayout = async () => {
  if (!previewContainer.value || !sidebarRef.value?.settings) {
    console.error('Preview container or settings not available')
    return
  }
  
  console.log('🔒 Starting freeze layout...')
  
  // Этап 1: Найти все page-break маркеры
  const contentContainer = previewContainer.value.querySelector('.mx-auto')
  if (!contentContainer) {
    console.error('Content container not found')
    return
  }
  
  const pageBreaks = Array.from(contentContainer.querySelectorAll('.page-break'))
  console.log(`Found ${pageBreaks.length} page breaks`)
  
  if (pageBreaks.length === 0) {
    console.error('No page breaks found - run calculatePageBreaks() first')
    return
  }
  
  // Этап 2: Для каждой страницы извлечь посты и их координаты
  const frozenPages = []
  const containerRect = contentContainer.getBoundingClientRect()
  
  pageBreaks.forEach((pageBreak, pageIndex) => {
    const pageNumber = pageIndex + 1
    console.log(`\n📄 Processing page ${pageNumber}...`)
    
    // Координаты начала страницы (относительно контейнера)
    const pageBreakRect = pageBreak.getBoundingClientRect()
    const pageTop = pageBreakRect.bottom // После page-break начинается контент страницы
    const pageLeft = containerRect.left
    
    // Найти все посты между этим и следующим page-break
    const nextPageBreak = pageBreaks[pageIndex + 1]
    const postsOnPage = findPostsBetweenMarkers(pageBreak, nextPageBreak, contentContainer)
    
    console.log(`  Found ${postsOnPage.length} posts on page ${pageNumber}`)
    
    // Извлечь координаты каждого поста
    const frozenPosts = postsOnPage.map(postElement => {
      const postRect = postElement.getBoundingClientRect()
      
      // Координаты относительно начала СТРАНИЦЫ
      const bounds = {
        top: pxToMm(postRect.top - pageTop),
        left: pxToMm(postRect.left - pageLeft),
        width: pxToMm(postRect.width),
        height: pxToMm(postRect.height)
      }
      
      const telegram_id = postElement.dataset.postId
      const channel_id = postElement.dataset.channelId
      
      console.log(`    Post ${telegram_id}: top=${bounds.top.toFixed(2)}mm, left=${bounds.left.toFixed(2)}mm`)
      
      // Извлекаем координаты медиа элементов внутри поста
      const mediaElements = []
      
      // Одиночные изображения (контейнер .post-media.single-image)
      // Фильтруем только photo и image/*, исключаем MessageMediaWebPage
      const singleImageContainers = postElement.querySelectorAll('.post-media.single-image')
      singleImageContainers.forEach(container => {
        const mediaType = container.dataset.mediaType
        const mimeType = container.dataset.mimeType
        
        // Только MessageMediaPhoto или MessageMediaDocument с image/*
        if (mediaType === 'MessageMediaPhoto' || 
            (mediaType === 'MessageMediaDocument' && mimeType && mimeType.startsWith('image/'))) {
          const containerRect = container.getBoundingClientRect()
          mediaElements.push({
            type: 'image',
            bounds: {
              top: pxToMm(containerRect.top - pageTop),
              left: pxToMm(containerRect.left - pageLeft),
              width: pxToMm(containerRect.width),
              height: pxToMm(containerRect.height)
            }
          })
        }
      })
      
      return {
        telegram_id: parseInt(telegram_id),
        channel_id: channel_id,
        type: postElement.dataset.isComment === 'true' ? 'comment' : 'post',
        bounds: bounds,
        media: mediaElements
      }
    })
    
    frozenPages.push({
      page_number: pageNumber,
      posts: frozenPosts
    })
  })
  
  console.log(`\n✅ Freeze complete: ${frozenPages.length} pages processed`)
  
  // Этап 3 и 4: Сохранить в БД через API
  try {
    await api.post(`/api/pages/${channelId}`, {
      channel_id: channelId,
      pages: frozenPages
    })
    console.log('💾 Saved to database')
  } catch (error) {
    console.error('Error saving frozen layout:', error)
  }
  
  return frozenPages
}

// Вспомогательная функция: найти посты между двумя page-break маркерами
const findPostsBetweenMarkers = (startMarker, endMarker, container) => {
  const allPosts = Array.from(container.querySelectorAll('[data-post-id]'))
  
  const startRect = startMarker.getBoundingClientRect()
  const endRect = endMarker ? endMarker.getBoundingClientRect() : { top: Infinity }
  
  // Фильтруем посты, которые находятся между маркерами
  return allPosts.filter(post => {
    const postRect = post.getBoundingClientRect()
    return postRect.top >= startRect.bottom && postRect.top < endRect.top
  })
}

// Экспортируем функции для внешнего использования
defineExpose({ recalculatePages, freezeCurrentLayout })

// Сохраняем ссылку на функцию в window для доступа из Navbar и Sidebar
if (typeof window !== 'undefined') {
  window.__previewRecalculatePages = recalculatePages
  window.__previewFreeze = freezeCurrentLayout
}
if (typeof window !== 'undefined') {
  window.__previewRecalculatePages = recalculatePages
}

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
      
      // Применяем фильтры для определения скрытых медиа и постов
      allPosts = applyFilters(allPosts);
      
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
  pageBreak.className = 'page-break relative'
  
  // Добавляем padding-top для всех, кроме первой страницы
  if (pageNumber > 1) {
    pageBreak.style.paddingTop = 'var(--preview-padding-bottom)'
  }
  
  pageBreak.style.paddingBottom = 'var(--preview-padding-top)'
  pageBreak.innerHTML = `
    <div class="absolute left-0 w-full border-t-4 border-dashed border-blue-400"> <div class="absolute left-0 bottom-0 bg-blue-500 text-white px-3 py-1 rounded text-xs font-semibold">
      Страница ${pageNumber}
    </div></div>
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
  
  // Добавляем индикатор страницы 1 в самое начало contentContainer
  if (contentContainer) {
    const firstChild = contentContainer.firstChild
    contentContainer.insertBefore(createPageBreak(1), firstChild)
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

// Cleanup при unmount
onUnmounted(() => {
  if (process.client) {
    cleanup()
  }
})

// Пересчитываем при изменении настроек печати
watch(() => sidebarRef.value?.settings, () => {
  nextTick(() => {
    calculatePageBreaks()
  })
}, { deep: true })
</script>
