<template>
  <div class="max-w-7xl mx-auto p-4 print:max-w-none">
    <!-- Информация о канале -->
    <ChannelCover
      v-if="channelInfo"
      :channel="channelInfo"
      :postsCount="pagesCount"
      :commentsCount="0"
    />

    <!-- Панель управления -->
    <div class="flex justify-between items-center mb-4 p-4 bg-white rounded-lg shadow">
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

    <!-- Vue Grid Layout контейнер -->
    <ClientOnly>
      <div v-if="gridLoaded && layout && layout.length > 0" class="relative bg-gray-50 rounded-lg p-4 border">
        <component
          :is="GridLayout"
          v-model:layout="layout"
          :col-num="12"
          :row-height="100"
          :is-draggable="isEditMode"
          :is-resizable="isEditMode"
          :is-mirrored="false"
          :vertical-compact="true"
          :margin="[10, 10]"
          :use-css-transforms="true"
          @layout-updated="handleLayoutUpdated"
        >
          <component
            :is="GridItem"
            v-for="item in layout"
            :key="item.i"
            :x="item.x"
            :y="item.y"
            :w="item.w"
            :h="item.h"
            :i="item.i"
            :static="!isEditMode"
            class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
          >
            <div class="h-full flex flex-col">
              <!-- Заголовок блока с кнопкой удаления -->
              <div v-if="isEditMode" class="flex justify-between items-center p-2 bg-gray-100 border-b border-gray-200">
                <span class="text-xs text-gray-600 font-medium">{{ item.i }}</span>
                <button
                  @click="handleDeleteBlock(item.i)"
                  class="text-red-500 hover:text-red-700 text-sm font-bold"
                  title="Удалить блок"
                >
                  ✕
                </button>
              </div>
              
              <!-- Контент блока -->
              <div class="flex-1 overflow-auto">
                <PageBlock
                  :block-id="item.i"
                  :content="item.content"
                  :is-edit-mode="isEditMode"
                  :channel-posts="channelPosts"
                  @edit="handleEditBlock"
                  @delete="handleDeleteBlock"
                />
              </div>
            </div>
          </component>
        </component>
      </div>

      <!-- Заглушка загрузки -->
      <div v-else class="text-center p-8 bg-gray-100 rounded-lg">
        <p class="text-gray-600">Загрузка страницы...</p>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { shallowRef } from 'vue'
import ChannelCover from '~/components/ChannelCover.vue'
import PageBlock from '~/components/PageBlock.vue'
import { api } from '~/services/api'
import { usePages } from '~/composables/usePages'

const route = useRoute()
const channelId = route.params.channelId
const isEditMode = ref(false)
const saveStatus = ref(null) // 'saving', 'saved', 'error'
const currentPage = ref(null)
const layout = ref([])
const saveTimeout = ref(null)
const channelPosts = ref([]) // Посты канала для передачи в блоки

// Компоненты Vue Grid Layout (загружаются на клиенте)
const GridLayout = shallowRef(null)
const GridItem = shallowRef(null)
const gridLoaded = ref(false)

const { createPage, loadChannelPages, saveLayout, blocksToLayout, layoutToBlocks } = usePages()

// Загрузка информации о канале
const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

// Загрузка постов канала
const loadChannelPosts = async () => {
  try {
    const response = await api.get(`/api/posts?channel_id=${channelId}`)
    channelPosts.value = response.data
  } catch (error) {
    console.error('Error loading channel posts:', error)
  }
}

// Загружаем посты при инициализации
await loadChannelPosts()

// Загрузка или создание страницы
const initializePage = async () => {
  try {
    const pages = await loadChannelPages(channelId)
    
    if (pages && pages.length > 0) {
      // Используем первую страницу
      currentPage.value = pages[0]
      
      // Если нет блоков, создаем демо-блоки
      if (!currentPage.value.json_data.blocks || currentPage.value.json_data.blocks.length === 0) {
        const demoBlocks = [
          {
            id: 'block-1',
            x: 0,
            y: 0,
            w: 4,
            h: 2,
            content: {
              title: 'Элемент 1',
              description: 'Демо-контент страницы'
            }
          },
          {
            id: 'block-2',
            x: 4,
            y: 0,
            w: 4,
            h: 2,
            content: {
              title: 'Элемент 2',
              description: 'Еще один демо-элемент'
            }
          },
          {
            id: 'block-3',
            x: 0,
            y: 2,
            w: 6,
            h: 2,
            content: {
              title: 'Элемент 3',
              description: 'Третий элемент сетки'
            }
          },
          {
            id: 'block-4',
            x: 6,
            y: 0,
            w: 2,
            h: 4,
            content: {
              title: 'Элемент 4',
              description: 'Боковой элемент'
            }
          }
        ]
        
        currentPage.value.json_data.blocks = demoBlocks
        await saveLayout(currentPage.value.id, demoBlocks, currentPage.value.json_data)
      }
      
      // Преобразуем блоки в layout для Vue Grid Layout
      layout.value = blocksToLayout(currentPage.value.json_data.blocks || [])
    } else {
      // Создаем новую страницу с демо-блоками
      const newPage = await createPage(channelId)
      
      // Добавляем демо-блоки
      const demoBlocks = [
        {
          id: 'block-1',
          x: 0,
          y: 0,
          w: 4,
          h: 2,
          content: {
            title: 'Элемент 1',
            description: 'Демо-контент страницы'
          }
        },
        {
          id: 'block-2',
          x: 4,
          y: 0,
          w: 4,
          h: 2,
          content: {
            title: 'Элемент 2',
            description: 'Еще один демо-элемент'
          }
        },
        {
          id: 'block-3',
          x: 0,
          y: 2,
          w: 6,
          h: 2,
          content: {
            title: 'Элемент 3',
            description: 'Третий элемент сетки'
          }
        },
        {
          id: 'block-4',
          x: 6,
          y: 0,
          w: 2,
          h: 4,
          content: {
            title: 'Элемент 4',
            description: 'Боковой элемент'
          }
        }
      ]
      
      newPage.json_data.blocks = demoBlocks
      
      // Сохраняем страницу с демо-блоками
      await saveLayout(newPage.id, demoBlocks, newPage.json_data)
      currentPage.value = newPage
      layout.value = blocksToLayout(demoBlocks)
    }
  } catch (error) {
    console.error('Error initializing page:', error)
  }
}

// Инициализация при загрузке
await initializePage()

// Загрузка компонентов Vue Grid Layout на клиенте
onMounted(async () => {
  if (process.client) {
    try {
      const vueGridLayout = await import('vue-grid-layout-v3')
      GridLayout.value = vueGridLayout.GridLayout
      GridItem.value = vueGridLayout.GridItem
      gridLoaded.value = true
    } catch (error) {
      console.error('Error loading vue-grid-layout-v3:', error)
    }
  }
})

const pagesCount = computed(() => {
  return currentPage.value ? 1 : 0
})

const saveStatusText = computed(() => {
  switch (saveStatus.value) {
    case 'saving': return '💾 Сохранение...'
    case 'saved': return '✓ Сохранено'
    case 'error': return '✗ Ошибка сохранения'
    default: return ''
  }
})

// Автосохранение при изменении layout
const autoSave = async () => {
  if (!currentPage.value) return
  
  try {
    saveStatus.value = 'saving'
    
    // Преобразуем layout обратно в блоки с сохранением content
    const blocks = layoutToBlocks(layout.value, currentPage.value.json_data.blocks)
    
    // Обновляем текущую страницу
    currentPage.value.json_data.blocks = blocks
    
    // Сохраняем в базу
    await saveLayout(currentPage.value.id, blocks, currentPage.value.json_data)
    
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

// Обработчик изменения layout (с debounce)
const handleLayoutUpdated = (newLayout) => {
  if (!isEditMode.value) return
  
  // Очищаем предыдущий таймаут
  if (saveTimeout.value) {
    clearTimeout(saveTimeout.value)
  }
  
  // Устанавливаем новый таймаут для сохранения
  saveTimeout.value = setTimeout(() => {
    autoSave()
  }, 500) // Сохраняем через 500мс после последнего изменения
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
    // Удаляем блок из layout
    const index = layout.value.findIndex(item => item.i === blockId)
    if (index !== -1) {
      layout.value.splice(index, 1)
      
      // Сохраняем изменения
      await autoSave()
    }
  } catch (error) {
    console.error('Error deleting block:', error)
    alert('Ошибка при удалении блока')
  }
}
</script>
