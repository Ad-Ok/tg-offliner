import { defineStore } from 'pinia'

export const useEditModeStore = defineStore('editMode', {
  state: () => {
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
    },

    disableExportMode() {
      this.isExportMode = false
    },

    // Проверяем и устанавливаем режим экспорта
    checkAndSetExportMode() {
      try {
        let isExport = false
        
        if (typeof window !== 'undefined') {
          // На клиенте проверяем URL
          const urlParams = new URLSearchParams(window.location.search)
          isExport = urlParams.get('export') === '1'
        } else {
          // На сервере проверяем через текущий route
          try {
            const route = useRoute()
            isExport = route.query.export === '1' || route.query.export === 'true'
          } catch (e) {
            // Route недоступен
          }
        }
        
        if (isExport !== this.isExportMode) {
          this.isExportMode = isExport
        }
        
        return isExport
      } catch (error) {
        return false
      }
    }
  }
})
