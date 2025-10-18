<template>
  <div class="group-editor relative">
    <button
      v-if="editModeStore.showDeleteButtons"
      class="btn btn-sm btn-outline btn-primary print:hidden disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="isProcessing"
      :title="buttonTitle"
      @click="reloadLayout"
    >
      <span v-if="isProcessing">⏳</span>
      <span v-else>Reload Layout</span>
    </button>
  <p v-if="feedbackMessage" :class="['mt-2', 'text-xs', feedbackClass]">
      {{ feedbackMessage }}
    </p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useEditModeStore } from '~/stores/editMode'

const props = defineProps({
  groupedId: {
    type: [String, Number],
    required: true
  },
  channelId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['layoutReloaded'])

const editModeStore = useEditModeStore()
const isProcessing = ref(false)
const feedbackMessage = ref('')
const isError = ref(false)

const buttonTitle = computed(() => {
  if (isProcessing.value) {
    return 'Regenerating layout...'
  }
  return 'Regenerate gallery layout'
})

const feedbackClass = computed(() => (isError.value ? 'text-error' : 'text-success'))

const reloadLayout = async () => {
  if (isProcessing.value) return

  isProcessing.value = true
  feedbackMessage.value = ''
  isError.value = false

  try {
    const { layoutsService } = await import('~/services/layoutsService.js')
    const response = await layoutsService.reloadLayout(props.groupedId, props.channelId)

    emit('layoutReloaded', response?.layout ?? null)
    feedbackMessage.value = 'Layout regenerated'
  } catch (error) {
    console.error('Failed to reload layout:', error)
    isError.value = true
    feedbackMessage.value = error?.response?.data?.error || 'Failed to regenerate layout'
  } finally {
    isProcessing.value = false
  }
}
</script>
