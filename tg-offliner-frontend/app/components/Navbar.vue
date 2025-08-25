<template>
  <div class="navbar bg-base-100 shadow-lg">
    <div class="navbar-start">
      <!-- Mobile menu -->
      <div class="dropdown">
        <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" />
          </svg>
        </div>
        <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <li><NuxtLink to="/">🏠 Главная</NuxtLink></li>
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
          <NuxtLink 
            to="/" 
            class="btn btn-ghost"
            :class="{ 'btn-active': $route.path === '/' }"
          >
            🏠 Главная
          </NuxtLink>
        </li>
      </ul>
    </div>
    
    <!-- Actions -->
    <div class="navbar-end">
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
      
      <button class="btn btn-primary ml-2">
        ⚡ Синхронизация
      </button>
    </div>
  </div>
</template>

<script setup>
// DaisyUI компоненты работают автоматически без дополнительных импортов
</script>
