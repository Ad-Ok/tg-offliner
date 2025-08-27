import { defineStore } from 'pinia'

export const useEditModeStore = defineStore('editMode', {
  state: () => {
    // Простая инициализация без сложной логики
    console.log('🔍 Store initialization')
    
    return {
      isEditMode: false,
      isExportMode: false
    }
  },

  getters: {
    showDeleteButtons: (state) => state.isEditMode && !state.isExportMode
  },

  actions: {
    toggleEditMode() {
      this.isEditMode = !this.isEditMode
    },

    enableEditMode() {
      this.isEditMode = true
    },

    disableEditMode() {
      this.isEditMode = false
    },

    enableExportMode() {
      this.isExportMode = true
      console.log('🔍 Export mode enabled manually')
    },

    disableExportMode() {
      this.isExportMode = false
      console.log('🔍 Export mode disabled manually')
    },

    // Проверяем и устанавливаем режим экспорта
    checkAndSetExportMode() {
      try {
        let isExport = false
        
        if (typeof window !== 'undefined') {
          // На клиенте проверяем URL
          const urlParams = new URLSearchParams(window.location.search)
          isExport = urlParams.get('export') === '1'
          console.log('🔍 [CLIENT] Export mode from URL:', isExport)
        } else {
          // На сервере проверяем через текущий route
          try {
            const route = useRoute()
            isExport = route.query.export === '1' || route.query.export === 'true'
            console.log('🔍 [SSR] Export mode from route:', isExport, 'Query:', route.query)
          } catch (e) {
            console.log('🔍 [SSR] Could not get route:', e.message)
          }
        }
        
        if (isExport !== this.isExportMode) {
          this.isExportMode = isExport
          console.log('🔍 Export mode updated to:', isExport)
        }
        
        return isExport
      } catch (error) {
        console.error('❌ Error checking export mode:', error)
        return false
      }
    }
  }
})
