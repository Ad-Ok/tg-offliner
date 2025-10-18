<template>
  <div class="post-editor">
    <!-- Кнопка скрытия/показа поста -->
    <button 
      v-if="editModeStore.showDeleteButtons"
      @click="toggleVisibility"
      :disabled="isSaving"
      :class="isHidden ? 'btn-info' : 'btn-error'"
      class="absolute top-2 left-full ml-2 z-10 btn btn-circle btn-sm btn-outline text-xl print:hidden disabled:opacity-50 disabled:cursor-not-allowed"
      :title="isSaving ? 'Сохранение...' : (isHidden ? 'Показать пост' : 'Скрыть пост')"
    >
      <span v-if="isSaving">⏳</span>
      <span v-else-if="isHidden">👁</span>
      <span v-else>×</span>
    </button>
    
    <!-- Здесь будут другие инструменты редактирования -->
  </div>
</template>

<script setup>
import { useEditModeStore } from '~/stores/editMode'
import { usePostEdit } from '~/composables/usePostEdit'

const props = defineProps({
  post: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['hiddenStateChanged'])

const editModeStore = useEditModeStore()
const { isHidden, isSaving, togglePostVisibility } = usePostEdit(props.post)

// Отслеживаем изменения состояния скрытости и уведомляем родительский компонент
watch(isHidden, (newValue) => {
  emit('hiddenStateChanged', newValue)
}, { immediate: true })

const toggleVisibility = async () => {
  await togglePostVisibility()
}
</script>
