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
        <!-- Навигация по chunks -->
        <ChunkNavigation
          v-if="chunksInfo && chunksInfo.total_chunks > 1"
          :chunksInfo="chunksInfo"
          v-model:currentChunk="currentChunk"
          :loading="pending"
          @chunkSelected="onChunkSelected"
        />
        
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
import ChunkNavigation from '~/components/ChunkNavigation.vue'
import PrintSettingsSidebar from '~/components/system/PrintSettingsSidebar.vue'
import { api } from '~/services/api'
import { getChannelPosts, getChannelChunks } from '~/services/apiV2'
import { transformV2PostsToFlat } from '~/utils/v2Adapter'
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

// Chunk state
const currentChunk = ref(null) // null = все посты
const chunksInfo = ref(null)

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
  
  // Этап 1.5: Используем layouts из уже загруженных V2 данных
  console.log('📦 Using preloaded gallery layouts from V2 response...')
  const galleryLayouts = new Map() // grouped_id -> layout
  
  if (posts.value) {
    posts.value.forEach(post => {
      if (post.grouped_id && post.layout) {
        galleryLayouts.set(String(post.grouped_id), post.layout)
      }
    })
  }
  
  console.log(`📦 Found ${galleryLayouts.size} gallery layouts from V2 data`)
  
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
      const isComment = postElement.dataset.isComment === 'true'
      
      // Извлекаем дату из data-атрибута или из .post-date (только для постов, не для комментариев)
      let post_date = ''
      if (!isComment) {
        post_date = postElement.dataset.date || ''
        if (!post_date) {
          const dateElement = postElement.querySelector('.post-date')
          if (dateElement) {
            post_date = dateElement.textContent.trim()
          }
        }
      }
      
      console.log(`    Post ${telegram_id}: top=${bounds.top.toFixed(2)}mm, left=${bounds.left.toFixed(2)}mm, date=${post_date}, isComment=${isComment}`)
      
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
          
          // Пропускаем скрытые элементы (display:none возвращает нулевой rect)
          if (containerRect.width <= 0 || containerRect.height <= 0) {
            console.log(`      ⏭️ Skipping hidden/zero-size media element: ${mediaType} (${containerRect.width}x${containerRect.height})`)
            return
          }
          
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
      
      // Галереи (группы постов) - ищем .gallery-container с .gallery-item элементами
      const galleryContainer = postElement.querySelector('.gallery-container')
      if (galleryContainer) {
        // Получаем grouped_id из data-grouped-id контейнера группы
        const groupElement = postElement.closest('[data-grouped-id]')
        const groupedId = groupElement ? groupElement.dataset.groupedId : null
        
        // Получаем border_width из предзагруженного layout
        let galleryBorderWidth = '0'
        if (groupedId && galleryLayouts.has(groupedId)) {
          const layout = galleryLayouts.get(groupedId)
          galleryBorderWidth = layout.border_width || '0'
          console.log(`    Gallery ${groupedId}: using border_width=${galleryBorderWidth}`)
        }
        
        const galleryItems = galleryContainer.querySelectorAll('.gallery-item')
        console.log(`    Found ${galleryItems.length} gallery items`)
        
        galleryItems.forEach((item, idx) => {
          // Telegram ID находится в атрибуте самого .gallery-item
          const galleryPostId = item.dataset.postId
          console.log(`      Gallery item ${idx}: postId=${galleryPostId}`)
          
          if (!galleryPostId) {
            console.warn(`      Gallery item ${idx}: missing postId, skipping`)
            return
          }
          
          // Внутри каждого .gallery-item есть PostMedia с data-media-type
          const mediaElement = item.querySelector('[data-media-type]')
          if (!mediaElement) {
            console.warn(`      Gallery item ${idx}: no media element found`)
            return
          }
          
          const mediaType = mediaElement.dataset.mediaType
          const mimeType = mediaElement.dataset.mimeType
          
          // Только MessageMediaPhoto или MessageMediaDocument с image/*
          if (mediaType === 'MessageMediaPhoto' || 
              (mediaType === 'MessageMediaDocument' && mimeType && mimeType.startsWith('image/'))) {
            const itemRect = item.getBoundingClientRect()
            
            // Пропускаем скрытые элементы (display:none возвращает нулевой rect)
            if (itemRect.width <= 0 || itemRect.height <= 0) {
              console.log(`      ⏭️ Skipping hidden/zero-size gallery item: ${galleryPostId} (${itemRect.width}x${itemRect.height})`)
              return
            }
            
            const mediaItem = {
              type: 'image',
              telegram_id: parseInt(galleryPostId),
              bounds: {
                top: pxToMm(itemRect.top - pageTop),
                left: pxToMm(itemRect.left - pageLeft),
                width: pxToMm(itemRect.width),
                height: pxToMm(itemRect.height)
              },
              border_width: galleryBorderWidth  // Сохраняем border_width для этого изображения
            }
            
            mediaElements.push(mediaItem)
            console.log(`      ✅ Added gallery image: telegram_id=${galleryPostId}, bounds=${JSON.stringify(mediaItem.bounds)}`)
          } else {
            console.log(`      ⏭️ Skipping non-image media: ${mediaType}`)
          }
        })
      }
      
      return {
        telegram_id: parseInt(telegram_id),
        channel_id: channel_id,
        date: post_date,
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

// Загрузка данных через V2 API (один запрос вместо N+1)
const { data: v2Response, pending, refresh: refreshPosts } = await useAsyncData(
  'preview-posts',
  async () => {
    const options = {
      includeHidden: true,
      includeComments: true,
    }
    // Если выбран конкретный chunk
    if (currentChunk.value !== null) {
      options.chunk = currentChunk.value
    }
    const response = await getChannelPosts(channelId, options)
    return response
  }
)

// Посты: трансформируем V2 → flat формат для компонентов + фильтры
const posts = computed(() => {
  if (!v2Response.value?.posts) return []
  const flat = transformV2PostsToFlat(
    v2Response.value.posts,
    v2Response.value.channel?.discussion_group_id
  )
  return applyFilters(flat)
})

// Channel info из V2 response (отдельный запрос не нужен)
const channelInfo = computed(() => v2Response.value?.channel || null)

// Инициализируем sortOrder из настроек канала
watch(channelInfo, (newChannelInfo) => {
  const savedSort = newChannelInfo?.settings?.display?.sort_order
    || newChannelInfo?.changes?.sortOrder
  if (savedSort) {
    sortOrder.value = savedSort
  }
}, { immediate: true })

// Загрузка chunks metadata и обработчик выбора chunk
const onChunkSelected = async (chunkIndex) => {
  currentChunk.value = chunkIndex
  await refreshPosts()
  // Пересчитываем разрывы страниц после загрузки нового chunk
  nextTick(() => {
    calculatePageBreaks()
  })
}

// Загружаем chunks metadata при монтировании
onMounted(async () => {
  // Загружаем chunks metadata для навигации
  try {
    const meta = await getChannelChunks(channelId)
    if (meta && meta.total_chunks > 1) {
      chunksInfo.value = meta
    }
  } catch (e) {
    console.warn('[preview] Failed to load chunks metadata:', e)
  }
  
  nextTick(() => {
    calculatePageBreaks()
  })
})

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
  
  // Находим все посты и галереи как топ-левел элементы
  // wall-item - это семантический класс для top-level элементов в Wall.vue
  const items = wallContainer.value.querySelectorAll('.wall-item > .post-container, .wall-item > .group')
  
  // Удаляем старые разрывы страниц и классы из всего контейнера
  const contentContainer = previewContainer.value?.querySelector('.mx-auto')
  if (contentContainer) {
    const oldBreaks = contentContainer.querySelectorAll('.page-break')
    oldBreaks.forEach(br => br.remove())
  }
  
  // Удаляем класс break-before-page со всех элементов
  items.forEach(item => {
    item.classList.remove('break-before-page')
  })
  
  let currentPageHeight = 0
  let pageCount = 1
  const pagesData = [{ page: 1, posts: [] }] // Структура: [{ page: 1, posts: [{telegram_id, channel_id}] }]
  
  // Добавляем индикатор страницы 1 в самое начало contentContainer
  if (contentContainer) {
    const firstChild = contentContainer.firstChild
    contentContainer.insertBefore(createPageBreak(1), firstChild)
  }
  
  items.forEach((item, index) => {
    const itemHeight = item.offsetHeight
    
    // Для галереи берем data-telegram-id, для поста - data-post-id
    const telegramId = item.getAttribute('data-telegram-id') || item.getAttribute('data-post-id')
    const channelId = item.getAttribute('data-channel-id')
    
    // Если добавление этого элемента превысит высоту страницы
    if (currentPageHeight + itemHeight > pageHeight && currentPageHeight > 0) {
      // Добавляем класс break-before-page к текущему элементу (первому на новой странице)
      item.classList.add('break-before-page')
      
      // Вставляем визуальный индикатор разрыва страницы перед элементом
      pageCount++
      item.parentNode.insertBefore(createPageBreak(pageCount), item)
      
      // Сбрасываем счетчик высоты
      currentPageHeight = itemHeight
      pagesData.push({ page: pageCount, posts: [] })
    } else {
      currentPageHeight += itemHeight
    }
    
    // Добавляем элемент на текущую страницу
    if (telegramId && channelId) {
      pagesData[pagesData.length - 1].posts.push({
        telegram_id: parseInt(telegramId),
        channel_id: channelId
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

// Cleanup function to remove window references
const cleanup = () => {
  if (typeof window !== 'undefined') {
    delete window.__previewRecalculatePages
    delete window.__previewFreeze
  }
}
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
