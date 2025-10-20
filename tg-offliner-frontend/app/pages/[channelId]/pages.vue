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

    <!-- GridStack контейнер -->
    <ClientOnly>
      <div v-if="currentPage" class="grid-stack" ref="gridStackRef">
        <!-- Блоки будут добавляться динамически -->
        <div 
          v-for="block in currentPage.json_data.blocks" 
          :key="block.id"
          class="grid-stack-item"
          :gs-id="block.id"
          :gs-x="block.x"
          :gs-y="block.y"
          :gs-w="block.w"
          :gs-h="block.h"
        >
          <div class="grid-stack-item-content">
            <PageBlock
              :block-id="block.id"
              :content="block.content"
              :is-edit-mode="isEditMode"
              @edit="handleEditBlock"
              @delete="handleDeleteBlock"
            />
          </div>
        </div>
      </div>

      <!-- Заглушка если нет страницы -->
      <div v-else class="text-center p-8 bg-gray-100 rounded-lg">
        <p class="text-gray-600">Загрузка страницы...</p>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import ChannelCover from '~/components/ChannelCover.vue'
import PageBlock from '~/components/PageBlock.vue'
import { api } from '~/services/api'
import { useGridStack } from '~/composables/useGridStack'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'

const route = useRoute()
const channelId = route.params.channelId
const gridStackRef = ref(null)
const gridInstance = ref(null)
const isEditMode = ref(false)
const saveStatus = ref(null) // 'saving', 'saved', 'error'
const currentPage = ref(null)

const { createPage, loadChannelPages, saveLayout, serializeGridItems } = useGridStack()

// Загрузка информации о канале
const { data: channelInfo } = await useAsyncData(
  'channelInfo',
  () => api.get(`/api/channels/${channelId}`).then(res => res.data)
)

// Загрузка или создание страницы
const initializePage = async () => {
  try {
    const pages = await loadChannelPages(channelId)
    
    if (pages && pages.length > 0) {
      // Используем первую страницу
      currentPage.value = pages[0]
    } else {
      // Создаем новую страницу с демо-блоками
      const newPage = await createPage(channelId)
      
      // Добавляем демо-блоки
      newPage.json_data.blocks = [
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
      
      // Сохраняем страницу с демо-блоками
      await saveLayout(newPage.id, newPage.json_data.blocks, newPage.json_data)
      currentPage.value = newPage
    }
  } catch (error) {
    console.error('Error initializing page:', error)
  }
}

// Инициализация при загрузке
await initializePage()

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

// Автосохранение при изменении
const autoSave = async () => {
  if (!gridInstance.value || !currentPage.value) return
  
  try {
    saveStatus.value = 'saving'
    
    const items = gridInstance.value.save(false)
    const blocks = serializeGridItems(items)
    
    // Сохраняем с сохранением content из текущей страницы
    const blocksWithContent = blocks.map(block => {
      const existingBlock = currentPage.value.json_data.blocks.find(b => b.id === block.id)
      return {
        ...block,
        content: existingBlock?.content || {}
      }
    })
    
    await saveLayout(currentPage.value.id, blocksWithContent, currentPage.value.json_data)
    
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
  
  if (gridInstance.value) {
    if (isEditMode.value) {
      gridInstance.value.enable()
    } else {
      gridInstance.value.disable()
    }
  }
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
    // Удаляем блок из массива
    const blockIndex = currentPage.value.json_data.blocks.findIndex(b => b.id === blockId)
    if (blockIndex !== -1) {
      currentPage.value.json_data.blocks.splice(blockIndex, 1)
      
      // Удаляем из GridStack
      const element = document.querySelector(`[gs-id="${blockId}"]`)
      if (element && gridInstance.value) {
        gridInstance.value.removeWidget(element)
      }
      
      // Сохраняем изменения
      await saveLayout(
        currentPage.value.id, 
        currentPage.value.json_data.blocks, 
        currentPage.value.json_data
      )
    }
  } catch (error) {
    console.error('Error deleting block:', error)
    alert('Ошибка при удалении блока')
  }
}

// Инициализация GridStack
onMounted(() => {
  if (gridStackRef.value && currentPage.value) {
    gridInstance.value = GridStack.init({
      cellHeight: 100,
      column: 12,
      acceptWidgets: true,
      float: true,
      disableOneColumnMode: true,
      staticGrid: true // Начинаем в режиме просмотра
    }, gridStackRef.value)

    // Подписываемся на события изменения
    gridInstance.value.on('change', (event, items) => {
      if (isEditMode.value) {
        autoSave()
      }
    })
  }
})

// Очистка при размонтировании
onBeforeUnmount(() => {
  if (gridInstance.value) {
    gridInstance.value.destroy(false)
  }
})
</script>
