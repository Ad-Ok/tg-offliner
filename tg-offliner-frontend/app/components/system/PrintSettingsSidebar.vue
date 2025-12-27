<template>
  <div class="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 dark:border-gray-700">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Настройки печати
      </h2>
      <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
        Настройте параметры экспорта
      </p>
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
    
    <!-- Export buttons (footer) -->
    <div class="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
      <button 
        @click="saveAndExportPdf"
        :disabled="isExporting"
        class="btn btn-primary w-full"
      >
        <span v-if="isExportingPdf" class="loading loading-spinner loading-sm"></span>
        <svg v-else class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Экспорт в PDF
      </button>
      
      <button 
        @click="saveAndExportIdml"
        :disabled="isExporting"
        class="btn btn-secondary w-full"
      >
        <span v-if="isExportingIdml" class="loading loading-spinner loading-sm"></span>
        <svg v-else class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Экспорт в IDML
      </button>
      
      <button 
        @click="goBack"
        class="btn btn-ghost w-full"
      >
        ← Назад к постам
      </button>
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
  }
})

const emit = defineEmits(['export-pdf', 'export-idml'])

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

const isExportingPdf = ref(false)
const isExportingIdml = ref(false)
const isExporting = computed(() => isExportingPdf.value || isExportingIdml.value)

// Сохраняет настройки и экспортирует в PDF
const saveAndExportPdf = async () => {
  isExportingPdf.value = true
  try {
    // Сохраняем настройки в БД
    await api.put(`/api/channels/${props.channelId}`, {
      print_settings: settings.value
    })
    
    // Запускаем экспорт
    emit('export-pdf')
  } catch (error) {
    console.error('Error saving settings:', error)
  } finally {
    isExportingPdf.value = false
  }
}

// Сохраняет настройки и экспортирует в IDML
const saveAndExportIdml = async () => {
  isExportingIdml.value = true
  try {
    // Сохраняем настройки в БД
    await api.put(`/api/channels/${props.channelId}`, {
      print_settings: settings.value
    })
    
    // Запускаем экспорт
    emit('export-idml')
  } catch (error) {
    console.error('Error saving settings:', error)
  } finally {
    isExportingIdml.value = false
  }
}

// Вернуться назад к постам
const goBack = () => {
  navigateTo(`/${props.channelId}/posts`)
}
</script>
