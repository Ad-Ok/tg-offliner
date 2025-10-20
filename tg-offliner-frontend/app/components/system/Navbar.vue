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
            <ChannelExports 
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
        <li>
          <!-- Export Buttons - только на странице канала -->
          <ChannelExports 
            v-if="isChannelPage && route.params.channelId"
            :channelId="route.params.channelId"
          />
          <!-- <NuxtLink 
            to="/" 
            class="btn btn-ghost"
            :class="{ 'btn-active': $route.path === '/' }"
          >
            🏠 Главная
          </NuxtLink> -->
        </li>
      </ul>
    </div>
    
    <!-- Actions -->
    <div class="navbar-end">
      <!-- View Mode Toggle Button - только на странице канала -->
      <button 
        v-if="isChannelPage"
        @click="toggleViewMode"
        class="btn btn-outline btn-sm mr-3"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path v-if="!isGridMode" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
        </svg>
        {{ isGridMode ? 'Режим ленты' : 'Режим сетки' }}
      </button>
      
      <!-- Edit Mode Toggle Button - только на странице канала -->
      <button 
        v-if="isChannelPage"
        @click="editModeStore.toggleEditMode()"
        :class="editModeStore.isEditMode ? 'btn-error' : 'btn-outline'"
        class="btn btn-sm mr-3"
      >
        <svg v-if="!editModeStore.isEditMode" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        {{ editModeStore.isEditMode ? 'Выйти' : 'Редактировать' }}
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
import ChannelExports from '~/components/system/ChannelExports.vue'

// Используем store для режима редактирования
const editModeStore = useEditModeStore()

// Определяем, находимся ли мы на странице канала
const route = useRoute()
const isChannelPage = computed(() => {
  // Проверяем, что путь соответствует паттерну /[channelId]/posts или /[channelId]/pages
  return (route.path.includes('/posts') || route.path.includes('/pages')) && route.params.channelId
})

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
