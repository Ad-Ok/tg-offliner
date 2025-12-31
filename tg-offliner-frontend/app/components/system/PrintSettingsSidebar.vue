<template>
  <div class="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 dark:border-gray-700">
      <div class="flex items-center justify-between mb-1">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Настройки печати
        </h2>
      </div>
      <div class="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        <span class="font-medium">Превью печати. Страниц: {{ totalPages || 0 }}</span>
      </div>
    </div>
    
    <!-- Settings form -->
    <div class="flex-1 overflow-y-auto p-4 space-y-6">
      <!-- Размер страницы -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Размер страницы
        </label>
        <select 
          v-model="settings.page_size" 
          class="select select-bordered w-full"
        >
          <option value="A4">A4 ({{ PAGE_SIZES.A4.width }} × {{ PAGE_SIZES.A4.height }} мм)</option>
          <option value="A3">A3 ({{ PAGE_SIZES.A3.width }} × {{ PAGE_SIZES.A3.height }} мм)</option>
          <option value="USLetter">US Letter ({{ PAGE_SIZES.USLetter.width }} × {{ PAGE_SIZES.USLetter.height }} мм)</option>
          <option value="Tabloid">Tabloid ({{ PAGE_SIZES.Tabloid.width }} × {{ PAGE_SIZES.Tabloid.height }} мм)</option>
        </select>
      </div>
      
      <!-- Поля (margins) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Поля страницы (в миллиметрах)
        </label>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Верхнее</label>
            <input 
              v-model.number="settings.margins[0]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="1"
              min="0"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Левое</label>
            <input 
              v-model.number="settings.margins[1]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="1"
              min="0"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Нижнее</label>
            <input 
              v-model.number="settings.margins[2]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="1"
              min="0"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Правое</label>
            <input 
              v-model.number="settings.margins[3]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="1"
              min="0"
            />
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Миллиметры (мм)
        </p>
      </div>
      
      <!-- Количество колонок текста -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Колонки текста
        </label>
        <input 
          v-model.number="settings.text_columns" 
          type="number" 
          min="1" 
          max="3" 
          class="input input-bordered w-full"
        />
      </div>
      
      <!-- Расстояние между колонками -->
      <div v-if="settings.text_columns > 1">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Расстояние между колонками (мм)
        </label>
        <input 
          v-model.number="settings.column_gutter" 
          type="number" 
          class="input input-bordered w-full"
          step="1"
          min="0"
        />
      </div>
      
      <!-- Master page -->
      <div class="form-control">
        <label class="label cursor-pointer">
          <span class="label-text">Master Page (колонтитулы)</span>
          <input 
            v-model="settings.master_page_enabled" 
            type="checkbox" 
            class="checkbox"
          />
        </label>
      </div>
      
      <!-- Headers/Footers -->
      <div v-if="settings.master_page_enabled" class="form-control">
        <label class="label cursor-pointer">
          <span class="label-text">Включить колонтитулы</span>
          <input 
            v-model="settings.include_headers_footers" 
            type="checkbox" 
            class="checkbox"
          />
        </label>
      </div>
      
      <!-- Divider -->
      <div class="divider"></div>
      
      <!-- Freeze Layout кнопка -->
      <div>
        <button 
          @click="handleFreezeLayout"
          :disabled="isFreezing"
          class="btn btn-primary w-full"
        >
          <svg v-if="!isFreezing" class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
          </svg>
          <span v-if="isFreezing" class="loading loading-spinner loading-sm"></span>
          {{ isFreezing ? 'Freezing...' : 'Freeze Layout' }}
        </button>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Сохранить текущую разбивку на страницы с абсолютными координатами
        </p>
      </div>
      
      <!-- Divider -->
      <div class="divider"></div>
      
      <!-- Предпросмотр настроек -->
      <div class="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
        <h3 class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          ТЕКУЩИЕ НАСТРОЙКИ
        </h3>
        <div class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
          <div>Страница: {{ settings.page_size }}</div>
          <div>Поля: {{ settings.margins.join(', ') }} мм</div>
          <div>Колонок: {{ settings.text_columns }}</div>
          <div v-if="settings.text_columns > 1">
            Зазор: {{ settings.column_gutter }} мм
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { api } from '~/services/api'
import { PAGE_SIZES } from '~/utils/units'

const props = defineProps({
  channelId: {
    type: String,
    required: true
  },
  channelInfo: {
    type: Object,
    default: null
  },
  totalPages: {
    type: Number,
    default: 0
  }
})

// Настройки печати (по умолчанию или из канала)
const settings = ref({
  page_size: 'A4',
  margins: [20, 20, 20, 20], // top, left, bottom, right (в миллиметрах)
  text_columns: 1,
  column_gutter: 5, // в миллиметрах
  master_page_enabled: true,
  include_headers_footers: true
})

// Состояние для freeze
const isFreezing = ref(false)

// Обработчик кнопки Freeze Layout
const handleFreezeLayout = async () => {
  isFreezing.value = true
  try {
    // Вызываем функцию из preview.vue через window.__previewFreeze или emit
    if (typeof window !== 'undefined' && window.__previewFreeze) {
      await window.__previewFreeze()
      
      // Автоматически переходим на страницу frozen preview
      window.location.href = `/preview/${props.channelId}/frozen`
    } else {
      console.error('Preview freeze function not available')
    }
  } catch (error) {
    console.error('Error freezing layout:', error)
  } finally {
    isFreezing.value = false
  }
}

// Загружаем существующие настройки из канала
watch(() => props.channelInfo, (info) => {
  if (info?.print_settings) {
    settings.value = { ...settings.value, ...info.print_settings }
  }
}, { immediate: true })

// Автосохранение при изменении настроек
watch(settings, async (newSettings) => {
  try {
    await api.put(`/api/channels/${props.channelId}`, {
      print_settings: newSettings
    })
  } catch (error) {
    console.error('Error saving print settings:', error)
  }
}, { deep: true })

// Expose settings для доступа из родительского компонента
defineExpose({
  settings
})
</script>
