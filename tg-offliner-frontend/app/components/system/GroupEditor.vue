<template>
  <div class="group-editor relative">
    <div v-if="editModeStore.showDeleteButtons" class="flex items-center gap-2 pt-2 print:hidden">
      <select
        v-model="selectedColumns"
        class="select select-sm select-bordered w-52"
        :disabled="isProcessing"
        title="Number of layout columns"
      >
        <option value="auto">Auto</option>
        <option value="1">1 column</option>
        <option value="2">2 columns</option>
        <option value="3">3 columns</option>
        <option value="4">4 columns</option>
      </select>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          v-model="noCrop"
          class="checkbox checkbox-sm checkbox-primary"
          :disabled="isProcessing"
        />
        <span class="text-sm">Не вписывать в прямоугольник</span>
      </label>
      <button
        class="btn btn-sm btn-outline btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="isProcessing"
        :title="buttonTitle"
        @click="reloadLayout"
      >
        <span v-if="isProcessing">⏳</span>
        <span v-else>Reload Layout</span>
      </button>
    </div>
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
const selectedColumns = ref('auto')
const noCrop = ref(false)

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
    const columns = selectedColumns.value === 'auto' ? null : parseInt(selectedColumns.value)
    const response = await layoutsService.reloadLayout(props.groupedId, props.channelId, columns, noCrop.value)

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
