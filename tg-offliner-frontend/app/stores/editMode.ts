import { defineStore } from 'pinia'

export const useEditModeStore = defineStore('editMode', {
  state: () => ({
    isEditMode: false,
    isExportMode: false
  }),

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
    },

    disableExportMode() {
      this.isExportMode = false
    }
  }
})
