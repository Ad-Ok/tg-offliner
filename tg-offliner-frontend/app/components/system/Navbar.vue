<template>
  <div :class="['navbar', 'fixed', 'top-0', 'right-0', 'left-0', 'z-20', 'bg-base-100', 'shadow-lg', 'print:hidden', { 'hidden': isExportMode }]">
    <div class="navbar-start">
      <!-- Mobile menu -->
      <div class="dropdown">
        <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" />
          </svg>
        </div>
        <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <!-- Export buttons for mobile -->
          <li v-if="isChannelPage && route.params.channelId" class="p-2">
            <SystemChannelExports 
              :channelId="route.params.channelId"
            />
          </li>
          <!-- <li><NuxtLink to="/">🏠 Главная</NuxtLink></li> -->
        </ul>
      </div>
      
      <!-- Logo -->
      <NuxtLink to="/" class="btn btn-ghost text-xl">
        <div class="avatar placeholder">
          <div class="bg-primary text-primary-content rounded-full w-8">
            <span class="text-xs font-bold">TG</span>
          </div>
        </div>
        <span class="ml-2 font-bold">Telegram Offliner</span>
      </NuxtLink>
    </div>
    
    <!-- Desktop menu -->
    <div class="navbar-center hidden lg:flex">
      <ul class="menu menu-horizontal px-1">
        <li v-if="isChannelPage && route.params.channelId && !isPreviewPage">
          <!-- Print/Export buttons - показываем только на странице постов -->
          <div class="flex gap-2">
            <NuxtLink 
              :to="`/preview/${route.params.channelId}`"
              class="btn btn-sm btn-outline btn-primary"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
              </svg>
              Экспорт в IDML
            </NuxtLink>
            <button 
              @click="handleExportPdf"
              :disabled="isExportingPdf"
              class="btn btn-sm btn-outline btn-success"
            >
              <span v-if="isExportingPdf" class="loading loading-spinner loading-xs mr-1"></span>
              <svg v-else class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Печать в PDF
            </button>
            <button 
              @click="handleExportHtml"
              class="btn btn-sm btn-outline btn-info"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              Экспорт в HTML
            </button>
          </div>
        </li>
        
        <!-- Preview mode buttons -->
        <li v-if="isPreviewPage && route.params.channelId">
          <div class="flex gap-2">
            <button 
              @click="handleExportIdml"
              :disabled="isExportingIdml"
              class="btn btn-sm btn-secondary"
            >
              <span v-if="isExportingIdml" class="loading loading-spinner loading-xs mr-1"></span>
              <svg v-else class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Экспорт в IDML
            </button>
            
            <NuxtLink 
              :to="`/${route.params.channelId}/posts`"
              class="btn btn-sm btn-ghost"
            >
              ← Назад к постам
            </NuxtLink>
          </div>
        </li>
      </ul>
    </div>
    
    <!-- Actions -->
    <div class="navbar-end">
      <!-- View Mode Toggle Button - только на странице канала -->
      <!-- TODO: Режим сетки в разработке (WIP) -->
      <!-- <button 
        v-if="isChannelPage"
        @click="toggleViewMode"
        class="btn btn-outline btn-sm mr-3"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path v-if="!isGridMode" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
        </svg>
        {{ isGridMode ? 'Режим ленты' : 'Режим сетки' }}
      </button> -->
      
      <!-- Кнопка пересчета страниц - только в preview -->
      <button 
        v-if="isPreviewPage"
        @click="handleRecalculatePages"
        class="btn btn-sm btn-ghost mr-2"
        title="Пересчитать страницы"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
      </button>
      
      <!-- Универсальная кнопка редактирования для posts и preview -->
      <button 
        v-if="isChannelPage"
        @click="isPreviewPage ? editModeStore.togglePreviewEditMode() : editModeStore.toggleEditMode()"
        :class="(isPreviewPage ? editModeStore.isPreviewEditMode : editModeStore.isEditMode) ? 'btn-error' : 'btn-outline'"
        class="btn btn-sm mr-3"
      >
        <svg v-if="!(isPreviewPage ? editModeStore.isPreviewEditMode : editModeStore.isEditMode)" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        {{ (isPreviewPage ? editModeStore.isPreviewEditMode : editModeStore.isEditMode) ? 'Выйти' : 'Редактировать' }}
      </button>
      
      <div class="dropdown dropdown-end">
        <div tabindex="0" role="button" class="btn btn-ghost btn-circle">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zM12 13a1 1 0 110-2 1 1 0 010 2zM12 20a1 1 0 110-2 1 1 0 010 2z" />
          </svg>
        </div>
        <ul tabindex="0" class="menu dropdown-content z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <li><a>⚙️ Настройки</a></li>
          <li><a>📊 Статистика</a></li>
          <li><a>❓ Помощь</a></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useEditModeStore } from '~/stores/editMode'
import { eventBus } from '~/eventBus'
import { apiBase } from '~/services/api'

// Используем store для режима редактирования
const editModeStore = useEditModeStore()

// Определяем, находимся ли мы на странице канала
const route = useRoute()
const isChannelPage = computed(() => {
  // Проверяем, что путь соответствует паттерну /[channelId]/posts или /[channelId]/pages или /[channelId]/preview
  return (route.path.includes('/posts') || route.path.includes('/pages') || route.path.includes('/preview')) && route.params.channelId
})

// Определяем, находимся ли мы на странице preview
const isPreviewPage = computed(() => {
  return route.path.includes('/preview')
})

// Состояние для экспорта
const isExportingPdf = ref(false)
const isExportingIdml = ref(false)

// Обработчик пересчета страниц в preview
const handleRecalculatePages = () => {
  // Вызываем функцию, которую preview компонент сохранил в window
  if (typeof window !== 'undefined' && window.__previewRecalculatePages) {
    window.__previewRecalculatePages()
  } else {
    console.warn('Preview recalculate function not available')
  }
}

// Обработчик экспорта PDF
const handleExportPdf = async () => {
  const channelId = route.params.channelId
  isExportingPdf.value = true
  try {
    const res = await fetch(`${apiBase}/api/channels/${channelId}/print`)
    const contentType = res.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const result = await res.json()
      if (result.success) {
        const filePath = `downloads/${channelId}/${channelId}.pdf`
        const fileUrl = `http://localhost:5000/${filePath}`
        eventBus.showAlert(
          `PDF файл для канала <strong>${channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
          "success",
          { html: true }
        )
      } else {
        eventBus.showAlert(result.error || "Ошибка создания PDF", "danger")
      }
    }
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка создания PDF", "danger")
    console.error("Error creating PDF:", error)
  } finally {
    isExportingPdf.value = false
  }
}

// Обработчик экспорта IDML
const handleExportIdml = async () => {
  const channelId = route.params.channelId
  isExportingIdml.value = true
  try {
    const res = await fetch(`${apiBase}/api/channels/${channelId}/export-idml`)
    const contentType = res.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const result = await res.json()
      if (result.success) {
        const filePath = `downloads/${channelId}/${channelId}.idml`
        const fileUrl = `http://localhost:5000/${filePath}`
        eventBus.showAlert(
          `IDML файл для канала <strong>${channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
          "success",
          { html: true }
        )
      } else {
        eventBus.showAlert(result.error || "Ошибка создания IDML", "danger")
      }
    }
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка создания IDML", "danger")
    console.error("Error creating IDML:", error)
  } finally {
    isExportingIdml.value = false
  }
}

// Определяем, в каком режиме мы находимся
const isGridMode = computed(() => {
  return route.path.includes('/pages')
})

// Функция переключения режима просмотра
const toggleViewMode = () => {
  const channelId = route.params.channelId
  if (isGridMode.value) {
    // Переход на режим ленты (posts)
    navigateTo(`/${channelId}/posts`)
  } else {
    // Переход на режим сетки (pages)
    navigateTo(`/${channelId}/pages`)
  }
}

// Обработчик экспорта HTML
const handleExportHtml = async () => {
  const channelId = route.params.channelId
  try {
    const res = await fetch(`${apiBase}/api/channels/${channelId}/export-html`)
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    
    const filePath = `downloads/${channelId}/index.html`
    const fileUrl = `http://localhost:5000/${filePath}`
    eventBus.showAlert(
      `HTML файл для канала <strong>${channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
      "success",
      { html: true }
    )
    
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка создания HTML", "danger")
    console.error("Error exporting HTML:", error)
  }
}

// Определяем, находимся ли мы в режиме экспорта
const isExportMode = computed(() => {
  return route.query.export === '1'
})

// Сбрасываем режим редактирования при переходе на другую страницу
watch(() => route.path, (newPath) => {
  if (!newPath.includes('/posts') && !newPath.includes('/pages')) {
    editModeStore.disableEditMode()
  }
})
</script>
