export const usePostEdit = (post) => {
  const isHidden = ref(post.isHidden || false)
  const isSaving = ref(false)
  const isLoading = ref(false)
  
  const loadHiddenState = async () => {
    // V2: isHidden уже приходит в response, отдельный запрос не нужен
    // Оставляем для обратной совместимости — просто читаем из post
    if (post.isHidden !== undefined) {
      isHidden.value = post.isHidden
    }
  }

  const saveHiddenState = async (hidden) => {
    try {
      isSaving.value = true
      
      const { setPostVisibility } = await import('~/services/apiV2')
      
      await setPostVisibility(
        post.channel_id,
        post.telegram_id,
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
