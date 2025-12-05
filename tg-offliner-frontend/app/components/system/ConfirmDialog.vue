<template>
  <div v-if="isVisible" class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg">{{ title || 'Confirmation' }}</h3>
      <p class="py-4">{{ message }}</p>
      <div class="modal-action">
        <button 
          class="btn btn-outline"
          @click="handleCancel"
        >
          {{ cancelText || 'Cancel' }}
        </button>
        <button 
          class="btn"
          :class="confirmButtonClass"
          @click="handleConfirm"
        >
          {{ confirmText || 'Confirm' }}
        </button>
      </div>
    </div>
    <div class="modal-backdrop" @click="handleCancel"></div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmDialog',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: 'Confirmation'
    },
    message: {
      type: String,
      required: true
    },
    confirmText: {
      type: String,
      default: 'Confirm'
    },
    cancelText: {
      type: String,
      default: 'Cancel'
    },
    type: {
      type: String,
      default: 'primary'
    }
  },
  computed: {
    confirmButtonClass() {
      switch (this.type) {
        case 'error':
          return 'btn-error'
        case 'warning':
          return 'btn-warning'
        case 'success':
          return 'btn-success'
        case 'secondary':
          return 'btn-secondary'
        default:
          return 'btn-primary'
      }
    }
  },
  methods: {
    handleConfirm() {
      this.$emit('confirm')
    },
    handleCancel() {
      this.$emit('cancel')
    }
  }
}
</script>
