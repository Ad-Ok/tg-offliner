<template>
  <div class="flex gap-2">
    <button 
      @click="handlePrintPdf" 
      :disabled="isLoading"
      class="btn btn-xs btn-outline btn-primary"
      :class="{ 'btn-disabled': isLoading }"
    >
      <span v-if="isLoadingPdf" class="loading loading-spinner loading-xs mr-1"></span>
      <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      PDF
    </button>
    
    <button 
      @click="handleExportHtml" 
      :disabled="isLoading"
      class="btn btn-xs btn-outline btn-info"
      :class="{ 'btn-disabled': isLoading }"
    >
      <span v-if="isLoadingHtml" class="loading loading-spinner loading-xs mr-1"></span>
      <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
      HTML
    </button>
  </div>
</template>

<script setup>
import { eventBus } from "~/eventBus"
import { apiBase } from '~/services/api'

const props = defineProps({
  channelId: {
    type: String,
    required: true
  }
})

const isLoadingPdf = ref(false)
const isLoadingHtml = ref(false)

const isLoading = computed(() => isLoadingPdf.value || isLoadingHtml.value)

const handlePrintPdf = async () => {
  try {
    isLoadingPdf.value = true
    
    const res = await fetch(`${apiBase}/api/channels/${props.channelId}/print`)
    const contentType = res.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const result = await res.json()
      if (result.success) {
        const filePath = `downloads/${props.channelId}/${props.channelId}.pdf`;
        const fileUrl = `http://localhost:5000/${filePath}`;
        eventBus.showAlert(
          `PDF файл для канала <strong>${props.channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
          "success",
          { html: true }
        );
      } else {
        eventBus.showAlert(result.error || "Ошибка при создании PDF", "danger")
      }
    } else {
      eventBus.showAlert("Неожиданный ответ сервера", "danger")
    }
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка при создании PDF", "danger")
    console.error("Ошибка при создании PDF:", error)
  } finally {
    isLoadingPdf.value = false
  }
}

const handleExportHtml = async () => {
  try {
    isLoadingHtml.value = true
    
    const res = await fetch(`${apiBase}/api/channels/${props.channelId}/export-html`)
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    
    const filePath = `downloads/${props.channelId}/index.html`;
    const fileUrl = `http://localhost:5000/${filePath}`;
    eventBus.showAlert(
      `HTML файл для канала <strong>${props.channelId}</strong> успешно создан: <a href="${fileUrl}" target="_blank" class="link link-info" rel="noopener">${filePath}</a>`,
      "success",
      { html: true }
    )
    
  } catch (error) {
    eventBus.showAlert(error.message || "Ошибка при создании HTML", "danger")
    console.error("Ошибка при экспорте HTML:", error)
  } finally {
    isLoadingHtml.value = false
  }
}
</script>
