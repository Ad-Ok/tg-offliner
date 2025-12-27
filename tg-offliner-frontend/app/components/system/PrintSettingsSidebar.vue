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
          <option value="A4">A4 (210 × 297 мм)</option>
          <option value="A3">A3 (297 × 420 мм)</option>
          <option value="USLetter">US Letter (8.5 × 11″)</option>
          <option value="Tabloid">Tabloid (11 × 17″)</option>
        </select>
      </div>
      
      <!-- Поля (margins) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Поля страницы (в пунктах)
        </label>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Верхнее</label>
            <input 
              v-model.number="settings.margins[0]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="0.1"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Левое</label>
            <input 
              v-model.number="settings.margins[1]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="0.1"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Нижнее</label>
            <input 
              v-model.number="settings.margins[2]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="0.1"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Правое</label>
            <input 
              v-model.number="settings.margins[3]" 
              type="number" 
              class="input input-bordered input-sm w-full"
              step="0.1"
            />
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
          1 пункт = 0.3528 мм (стандарт InDesign)
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
          Расстояние между колонками (пункты)
        </label>
        <input 
          v-model.number="settings.column_gutter" 
          type="number" 
          class="input input-bordered w-full"
          step="0.1"
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
      
      <!-- Предпросмотр настроек -->
      <div class="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
        <h3 class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          ТЕКУЩИЕ НАСТРОЙКИ
        </h3>
        <div class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
          <div>Страница: {{ settings.page_size }}</div>
          <div>Поля: {{ settings.margins.join(', ') }} пт</div>
          <div>Колонок: {{ settings.text_columns }}</div>
          <div v-if="settings.text_columns > 1">
            Зазор: {{ settings.column_gutter }} пт
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { api } from '~/services/api'

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
  margins: [56.69, 56.69, 56.69, 56.69], // top, left, bottom, right (в пунктах)
  text_columns: 1,
  column_gutter: 14.17,
  master_page_enabled: true,
  include_headers_footers: true
})

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
