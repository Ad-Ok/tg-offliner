<template>
  <nav class="bg-white shadow-lg border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo and title -->
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <svg class="h-8 w-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
            </svg>
          </div>
          <NuxtLink to="/">
            <h1 class="text-xl font-bold text-gray-900">Telegram Offliner</h1>
            <p class="text-sm text-gray-500">Сохранение каналов Telegram</p>
          </NuxtLink>
        </div>

        <!-- Navigation menu -->
        <div class="hidden md:block">
          <div class="ml-10 flex items-baseline space-x-4">
            <NuxtLink 
              to="/" 
              class="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
              :class="{ 'text-blue-600 bg-blue-50': $route.path === '/' }"
            >
              Главная
            </NuxtLink>
          </div>
        </div>

        <!-- Mobile menu button -->
        <div class="md:hidden">
          <button 
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="text-gray-600 hover:text-gray-900 focus:outline-none focus:text-gray-900 p-2 rounded-md"
          >
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <div v-show="mobileMenuOpen" class="md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-1 border-t border-gray-200">
          <NuxtLink 
            to="/" 
            class="block text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-base font-medium transition-colors duration-200"
            :class="{ 'text-blue-600 bg-blue-50': $route.path === '/' }"
            @click="mobileMenuOpen = false"
          >
            Главная
          </NuxtLink>
          <NuxtLink 
            to="/channels" 
            class="block text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-base font-medium transition-colors duration-200"
            :class="{ 'text-blue-600 bg-blue-50': $route.path === '/channels' }"
            @click="mobileMenuOpen = false"
          >
            Каналы
          </NuxtLink>
          <NuxtLink 
            to="/export" 
            class="block text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-base font-medium transition-colors duration-200"
            :class="{ 'text-blue-600 bg-blue-50': $route.path === '/export' }"
            @click="mobileMenuOpen = false"
          >
            Экспорт
          </NuxtLink>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'

const mobileMenuOpen = ref(false)
</script>
