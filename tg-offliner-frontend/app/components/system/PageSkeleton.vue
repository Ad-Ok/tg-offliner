<template>
  <div 
    class="page-skeleton mb-8"
    :style="{ minHeight: `${height}px` }"
  >
    <!-- Заголовок страницы -->
    <div class="flex justify-between items-center mb-4 p-3 bg-gray-100 rounded-t-lg border-b animate-pulse">
      <div class="h-6 bg-gray-300 rounded w-32"></div>
      <div class="h-4 bg-gray-300 rounded w-20"></div>
    </div>

    <!-- Skeleton grid -->
    <div class="bg-gray-50 rounded-b-lg p-4 border border-t-0">
      <div class="grid grid-cols-12 gap-2">
        <!-- Несколько skeleton блоков -->
        <div 
          v-for="i in 3" 
          :key="i"
          class="col-span-4 h-32 bg-gray-200 rounded-lg animate-pulse"
        ></div>
      </div>
      
      <div class="text-center mt-4 text-gray-500 text-sm">
        ⏳ Загрузка страницы {{ pageNumber }}...
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  pageNumber: {
    type: Number,
    required: true
  },
  height: {
    type: Number,
    default: 700
  }
})
</script>

<style scoped>
.page-skeleton {
  transition: opacity 0.3s ease;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
