export const usePostEdit = (post) => {
  const isHidden = ref(post.isHidden || false)
  const isSaving = ref(false)
  const isLoading = ref(false)
  
  const loadHiddenState = async () => {
    if (post.isHidden !== undefined) {
      return
    }
    
    try {
      isLoading.value = true
      
      const { editsService } = await import('~/services/editsService.js')
      
      const hiddenState = await editsService.getPostHiddenState(
        post.telegram_id,
        post.channel_id
      )
      
      isHidden.value = hiddenState
      
    } catch (error) {
      console.error('Error loading post hidden state:', error)
      
    } finally {
      isLoading.value = false
    }
  }

  const saveHiddenState = async (hidden) => {
    try {
      isSaving.value = true
      
      const { editsService } = await import('~/services/editsService.js')
      
      await editsService.setPostHidden(
        post.telegram_id,
        post.channel_id,
        hidden
      )
      
    } catch (error) {
      console.error('Error saving post visibility state:', error)
      isHidden.value = !hidden
      
      alert('Ошибка при сохранении изменений. Попробуйте еще раз.')
      
    } finally {
      isSaving.value = false
    }
  }

  const hidePost = async () => {
    isHidden.value = true
    await saveHiddenState(true)
  }
  
  const showPost = async () => {
    isHidden.value = false
    await saveHiddenState(false)
  }
  
  const togglePostVisibility = async () => {
    if (isSaving.value) return
    
    if (isHidden.value) {
      await showPost()
    } else {
      await hidePost()
    }
  }

  onMounted(() => {
    loadHiddenState()
  })

  return {
    isHidden: readonly(isHidden),
    isSaving: readonly(isSaving),
    isLoading: readonly(isLoading),
    hidePost,
    showPost,
    togglePostVisibility,
    loadHiddenState
  }
}
