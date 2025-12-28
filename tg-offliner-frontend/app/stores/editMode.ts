import { defineStore } from 'pinia'

export const useEditModeStore = defineStore('editMode', {
  state: () => {
    // Простая инициализация без сложной логики
    console.log('🔍 Store initialization')
    
    return {
      isEditMode: false,
      isExportMode: false,
      isPreviewEditMode: false
    }
  },

  getters: {
    showDeleteButtons: (state) => (state.isEditMode || state.isPreviewEditMode) && !state.isExportMode,
    
    // Определяем текущую страницу на основе route
    isPostsPage: () => {
      if (typeof window === 'undefined') return false
      return window.location.pathname.includes('/posts')
    },
    
    isPreviewPage: () => {
      if (typeof window === 'undefined') return false
      return window.location.pathname.includes('/preview')
    }
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

    togglePreviewEditMode() {
      this.isPreviewEditMode = !this.isPreviewEditMode
    },

    enablePreviewEditMode() {
      this.isPreviewEditMode = true
    },

    disablePreviewEditMode() {
      this.isPreviewEditMode = false
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
