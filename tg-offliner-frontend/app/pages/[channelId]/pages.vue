<template>
  <div class="max-w-7xl mx-auto p-4 print:max-w-none">
    <!-- Информация о канале -->
    <ChannelCover
      v-if="channelInfo"
      :channel="channelInfo"
      :postsCount="totalPagesCount"
      :commentsCount="0"
    />

    <!-- Панель управления -->
    <div class="flex justify-between items-center mb-4 p-4 bg-white rounded-lg shadow sticky top-0 z-10">
      <div class="flex items-center gap-4">
        <h2 class="text-xl font-bold">Редактор страниц</h2>
        
        <!-- Индикатор режима -->
        <span 
          :class="[
            'px-3 py-1 rounded-full text-sm font-medium',
            isEditMode ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'
          ]"
        >
          {{ isEditMode ? '✏️ Редактирование' : '👁️ Просмотр' }}
        </span>

        <!-- Индикатор сохранения -->
        <span 
          v-if="saveStatus"
          :class="[
            'px-3 py-1 rounded-full text-sm',
            saveStatus === 'saving' ? 'bg-blue-100 text-blue-700' : '',
            saveStatus === 'saved' ? 'bg-green-100 text-green-700' : '',
            saveStatus === 'error' ? 'bg-red-100 text-red-700' : ''
          ]"
        >
          {{ saveStatusText }}
        </span>

        <!-- Индикатор позиции скролла -->
        <span class="text-sm text-gray-600">
          Страница {{ currentVisiblePage }} из {{ totalPagesCount }}
        </span>
        
        <!-- Индикатор загруженных страниц -->
        <span class="text-xs text-gray-500">
          (загружено: {{ loadedPagesCount }})
        </span>
      </div>

      <!-- Кнопки управления -->
      <div class="flex gap-2">
        <button
          @click="toggleEditMode"
          :class="[
            'px-4 py-2 rounded-lg font-medium transition-colors',
            isEditMode 
              ? 'bg-green-500 hover:bg-green-600 text-white' 
              : 'bg-orange-500 hover:bg-orange-600 text-white'
          ]"
        >
          {{ isEditMode ? '✓ Завершить редактирование' : '✏️ Редактировать' }}
        </button>
      </div>
    </div>

    <!-- Отладочная информация -->
    <div class="bg-blue-50 p-2 mb-4 rounded text-xs font-mono">
      <div class="grid grid-cols-2 gap-2">
        <div>📊 Виртуальных элементов: <strong>{{ virtualItems.length }}</strong></div>
        <div>📄 Всего страниц: <strong>{{ totalPagesCount }}</strong></div>
        <div>💾 Загружено в память: <strong>{{ loadedPagesCount }}</strong></div>
        <div>📍 Видимые индексы: <strong>{{ virtualItems.map(v => v.index + 1).join(', ') }}</strong></div>
        <div>📮 Постов в канале: <strong>{{ channelPosts.length }}</strong></div>
        <div>📏 Общая высота: <strong>{{ Math.round(totalHeight / 1000) }}k px</strong></div>
      </div>
    </div>

    <!-- Виртуализированный список страниц -->
    <ClientOnly>
      <div 
        ref="scrollContainer" 
        class="virtual-scroll-container"
        style="height: 600px; overflow-y: auto; border: 2px solid #ccc;"
      >
        <div 
          :style="{ 
            height: `${totalHeight}px`, 
            position: 'relative' 
          }"
        >
          <div
            v-for="virtualItem in virtualItems"
            :key="virtualItem.key"
            :style="{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }"
          >
            <!-- Загруженная страница -->
            <Page
              v-if="loadedPages[virtualItem.index]"
              :page="loadedPages[virtualItem.index]"
              :page-number="virtualItem.index + 1"
              :is-edit-mode="isEditMode"
              :channel-posts="channelPosts"
              @layout-updated="handleLayoutUpdated"
              @edit-block="handleEditBlock"
              @delete-block="handleDeleteBlock"
            />
            
            <!-- Skeleton для загружающихся страниц -->
            <PageSkeleton 
              v-else 
              :page-number="virtualItem.index + 1"
              :height="PAGE_HEIGHT"
            />
          </div>
        </div>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import ChannelCover from '~/components/ChannelCover.vue'
import Page from '~/components/system/Page.vue'
import PageSkeleton from '~/components/system/PageSkeleton.vue'
import { api } from '~/services/api'
import { getChannelPosts } from '~/services/apiV2'
import { transformV2PostsToFlat } from '~/utils/v2Adapter'
import { usePages } from '~/composables/usePages'

const route = useRoute()
const channelId = route.params.channelId
const isEditMode = ref(false)
const saveStatus = ref(null) // 'saving', 'saved', 'error'
const saveTimeout = ref(null)
const channelPosts = ref([]) // Посты канала для передачи в блоки

// Виртуализация
const scrollContainer = ref(null)
const PAGE_HEIGHT = 700 // Фиксированная высота страницы в пикселях
const POSTS_PER_PAGE = 4 // Постов на одну страницу

// Хранилище загруженных страниц: { [index]: pageData }
const loadedPages = ref({})
const loadingPages = ref(new Set()) // Страницы, которые сейчас загружаются

const { loadChannelPages, saveLayout } = usePages()

// V2: одним запросом загружаем и канал, и посты
const { data: v2Response } = await useAsyncData(
  'pages-channel-posts',
  () => getChannelPosts(channelId, { includeComments: true, includeHidden: true })
)

// Extract channel info and posts from V2 response
const channelInfo = computed(() => v2Response.value?.channel || null)

// Инициализируем channelPosts из V2 данных
if (v2Response.value?.posts) {
  const discussionId = v2Response.value.channel?.discussion_group_id
    ? String(v2Response.value.channel.discussion_group_id) : null
  channelPosts.value = transformV2PostsToFlat(v2Response.value.posts, discussionId)
}

// Вычисляем максимальное количество страниц на основе постов
const MAX_PAGES = computed(() => {
  const postsCount = channelPosts.value.length
  if (postsCount === 0) return 100 // Минимум 100 страниц если постов нет
  
  // Рассчитываем количество страниц: посты / 4 + 20% запас
  const calculatedPages = Math.ceil(postsCount / POSTS_PER_PAGE * 1.2)
  return Math.max(100, Math.min(calculatedPages, 1000)) // От 100 до 1000
})

// Загружаем начальные страницы (первые 3-5)
const initializePages = async () => {
  try {
    const initialPages = await loadChannelPages(channelId)
    
    console.log('Initial pages loaded:', initialPages)
    
    // Распределяем страницы по индексам
    initialPages.forEach((page, arrayIndex) => {
      // Проверяем, есть ли page_number в json_data
      const pageNumber = page.json_data?.page_number
      const index = pageNumber ? pageNumber - 1 : arrayIndex
      
      loadedPages.value[index] = page
      console.log(`Страница ${index} (номер ${pageNumber || 'не указан'}) загружена`)
    })
    
    console.log(`Загружено ${initialPages.length} начальных страниц`)
    console.log('LoadedPages:', Object.keys(loadedPages.value).map(k => `[${k}]`).join(', '))
  } catch (error) {
    console.error('Error initializing pages:', error)
  }
}

await initializePages()

// Общее количество страниц (уже computed выше)
const totalPagesCount = MAX_PAGES

// Количество фактически загруженных страниц
const loadedPagesCount = computed(() => Object.keys(loadedPages.value).length)

// Виртуализатор - useVirtualizer возвращает ref в Vue
const rowVirtualizer = useVirtualizer(computed(() => ({
  count: MAX_PAGES.value,
  getScrollElement: () => scrollContainer.value,
  estimateSize: () => PAGE_HEIGHT,
  overscan: 2, // Загружаем +2 страницы сверху и снизу
})))

// Виртуальные элементы для рендеринга
const virtualItems = computed(() => rowVirtualizer.value.getVirtualItems())

// Общая высота виртуального списка
const totalHeight = computed(() => rowVirtualizer.value.getTotalSize())

// Текущая видимая страница
const currentVisiblePage = computed(() => {
  const items = virtualItems.value
  return items.length > 0 ? items[0].index + 1 : 1
})

// Загрузка страницы по индексу
const loadPage = async (index) => {
  // Если уже загружена или загружается
  if (loadedPages.value[index] || loadingPages.value.has(index)) {
    console.log(`⏭️ Пропуск загрузки страницы index=${index} (уже есть)`)
    return
  }
  
  console.log(`⬇️ Начало загрузки страницы index=${index} (номер ${index + 1})`)
  loadingPages.value.add(index)
  
  try {
    // Пытаемся загрузить страницу из базы
    const response = await api.get(`/api/pages/${channelId}?page_number=${index + 1}`)
    
    if (response.data && response.data.length > 0) {
      // Страница существует в БД
      loadedPages.value[index] = response.data[0]
      console.log(`✅ Загружена страница index=${index} из БД`)
    } else {
      // Создаём новую страницу
      console.log(`🆕 Создаём новую страницу index=${index}`)
      const newPage = await api.post(`/api/pages`, {
        channel_id: channelId,
        page_number: index + 1,
        json_data: {
          blocks: [],
          settings: {}
        }
      })
      
      loadedPages.value[index] = newPage.data
      console.log(`✅ Создана новая страница index=${index}`)
    }
  } catch (error) {
    console.error(`❌ Ошибка загрузки страницы index=${index}:`, error)
    
    // Создаём пустую страницу локально при ошибке
    loadedPages.value[index] = {
      id: `temp-${index}`,
      channel_id: channelId,
      page_number: index + 1,
      json_data: {
        blocks: [],
        settings: {}
      }
    }
    console.log(`⚠️ Создана временная страница index=${index}`)
  } finally {
    loadingPages.value.delete(index)
    console.log(`🏁 Завершена загрузка index=${index}. В памяти: ${Object.keys(loadedPages.value).length} страниц`)
  }
}

// Очистка далёких страниц из памяти и загрузка видимых
watch(() => virtualItems.value, async (newItems) => {
  if (newItems.length === 0) return
  
  const visibleIndices = new Set(newItems.map(item => item.index))
  const bufferSize = 20 // Увеличили буфер до 20 страниц
  
  // Загружаем все видимые страницы + буфер
  const minVisible = Math.min(...visibleIndices)
  const maxVisible = Math.max(...visibleIndices)
  const loadMin = Math.max(0, minVisible - 2)
  const loadMax = Math.min(MAX_PAGES.value - 1, maxVisible + 2)
  
  console.log(`👁️ Видимые индексы: ${Array.from(visibleIndices).sort((a,b) => a-b).join(', ')}`)
  console.log(`📥 Нужно загрузить диапазон: ${loadMin}-${loadMax}`)
  
  // Загружаем недостающие страницы
  const loadPromises = []
  for (let i = loadMin; i <= loadMax; i++) {
    if (!loadedPages.value[i] && !loadingPages.value.has(i)) {
      console.log(`➕ Добавляем в очередь загрузки: index=${i}`)
      loadPromises.push(loadPage(i))
    }
  }
  
  if (loadPromises.length > 0) {
    console.log(`⏳ Загружаем ${loadPromises.length} страниц...`)
    await Promise.all(loadPromises)
    console.log(`✅ Загрузка завершена!`)
  } else {
    console.log(`✓ Все необходимые страницы уже загружены`)
  }
  
  // Определяем диапазон для хранения в памяти (больше, чем загружаем)
  const keepMin = Math.max(0, minVisible - bufferSize)
  const keepMax = Math.min(MAX_PAGES.value - 1, maxVisible + bufferSize)
  
  // Удаляем страницы вне диапазона
  Object.keys(loadedPages.value).forEach(index => {
    const idx = parseInt(index)
    if (idx < keepMin || idx > keepMax) {
      console.log(`Выгружаем страницу ${idx + 1} из памяти`)
      delete loadedPages.value[idx]
    }
  })
}, { deep: true })

const saveStatusText = computed(() => {
  switch (saveStatus.value) {
    case 'saving': return '💾 Сохранение...'
    case 'saved': return '✓ Сохранено'
    case 'error': return '✗ Ошибка сохранения'
    default: return ''
  }
})

// Обработчик изменения layout на любой странице
const handleLayoutUpdated = async ({ pageId, layout, blocks }) => {
  if (!isEditMode.value) return
  
  // Очищаем предыдущий таймаут
  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value)
  }
  
  // Устанавливаем новый таймаут для сохранения
  saveTimeout.value = setTimeout(async () => {
    await autoSave(pageId, blocks)
  }, 500) // Сохраняем через 500мс после последнего изменения
}

// Автосохранение при изменении layout
const autoSave = async (pageId, blocks) => {
  try {
    saveStatus.value = 'saving'
    
    // Находим страницу в loadedPages
    let pageIndex = -1
    let page = null
    
    for (const [index, pageData] of Object.entries(loadedPages.value)) {
      if (pageData.id === pageId) {
        pageIndex = parseInt(index)
        page = pageData
        break
      }
    }
    
    if (!page) {
      throw new Error('Page not found in loaded pages')
    }
    
    // Обновляем блоки
    page.json_data.blocks = blocks
    
    // Сохраняем в базу
    await saveLayout(pageId, blocks, page.json_data)
    
    saveStatus.value = 'saved'
    setTimeout(() => {
      saveStatus.value = null
    }, 2000)
  } catch (error) {
    console.error('Error auto-saving:', error)
    saveStatus.value = 'error'
    setTimeout(() => {
      saveStatus.value = null
    }, 3000)
  }
}

// Переключение режима редактирования
const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value
}

// Обработчик редактирования блока
const handleEditBlock = (blockId) => {
  console.log('Edit block:', blockId)
  // TODO: Открыть модальное окно для редактирования контента блока
  alert(`Редактирование блока ${blockId} будет реализовано в следующей фазе`)
}

// Обработчик удаления блока
const handleDeleteBlock = async (blockId) => {
  if (!confirm(`Удалить блок ${blockId}?`)) return
  
  try {
    // Находим страницу с этим блоком
    for (const [index, page] of Object.entries(loadedPages.value)) {
      const blockIndex = page.json_data.blocks.findIndex(b => b.id === blockId)
      if (blockIndex !== -1) {
        // Удаляем блок
        page.json_data.blocks.splice(blockIndex, 1)
        
        // Сохраняем изменения
        await autoSave(page.id, page.json_data.blocks)
        break
      }
    }
  } catch (error) {
    console.error('Error deleting block:', error)
    alert('Ошибка при удалении блока')
  }
}
</script>
