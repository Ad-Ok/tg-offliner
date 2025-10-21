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

        <!-- Количество страниц -->
        <span class="text-sm text-gray-600">
          Всего страниц: {{ totalPagesCount }}
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

    <!-- Список всех страниц -->
    <div v-if="pages && pages.length > 0" class="space-y-6">
      <Page
        v-for="(page, index) in pages"
        :key="page.id"
        :page="page"
        :page-number="index + 1"
        :is-edit-mode="isEditMode"
        :channel-posts="channelPosts"
        @layout-updated="handleLayoutUpdated"
        @edit-block="handleEditBlock"
        @delete-block="handleDeleteBlock"
      />
    </div>

    <!-- Заглушка если нет страниц -->
    <div v-else class="text-center p-8 bg-gray-100 rounded-lg">
      <p class="text-gray-600">Загрузка страниц...</p>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { ref, computed } from 'vue'
import ChannelCover from '~/components/ChannelCover.vue'
import Page from '~/components/system/Page.vue'
import { api } from '~/services/api'
import { usePages } from '~/composables/usePages'

const route = useRoute()
const channelId = route.params.channelId
const isEditMode = ref(false)
const saveStatus = ref(null) // 'saving', 'saved', 'error'
const pages = ref([]) // Все страницы канала
const saveTimeout = ref(null)
const channelPosts = ref([]) // Посты канала для передачи в блоки

const { loadChannelPages, saveLayout } = usePages()

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

// Загрузка всех страниц канала
const initializePages = async () => {
  try {
    const loadedPages = await loadChannelPages(channelId)
    pages.value = loadedPages || []
  } catch (error) {
    console.error('Error initializing pages:', error)
  }
}

// Инициализация при загрузке
await initializePages()

// Общее количество страниц
const totalPagesCount = computed(() => pages.value.length)

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
    
    // Находим страницу в массиве
    const pageIndex = pages.value.findIndex(p => p.id === pageId)
    if (pageIndex === -1) {
      throw new Error('Page not found')
    }
    
    const page = pages.value[pageIndex]
    
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
    for (const page of pages.value) {
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
