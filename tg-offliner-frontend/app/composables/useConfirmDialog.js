import { ref } from 'vue'

const isDialogVisible = ref(false)
const dialogConfig = ref({
  title: '',
  message: '',
  confirmText: 'Подтвердить',
  cancelText: 'Отмена',
  type: 'primary'
})

let resolvePromise = null

export const useConfirmDialog = () => {
  const showConfirmDialog = (config) => {
    return new Promise((resolve) => {
      dialogConfig.value = {
        title: config.title || 'Подтверждение',
        message: config.message,
        confirmText: config.confirmText || 'Подтвердить',
        cancelText: config.cancelText || 'Отмена',
        type: config.type || 'primary'
      }
      
      isDialogVisible.value = true
      resolvePromise = resolve
    })
  }

  const handleConfirm = () => {
    isDialogVisible.value = false
    if (resolvePromise) {
      resolvePromise(true)
      resolvePromise = null
    }
  }

  const handleCancel = () => {
    isDialogVisible.value = false
    if (resolvePromise) {
      resolvePromise(false)
      resolvePromise = null
    }
  }

  return {
    isDialogVisible,
    dialogConfig,
    showConfirmDialog,
    handleConfirm,
    handleCancel
  }
}
