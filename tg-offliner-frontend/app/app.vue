<template>
  <div>
    <link v-if="$route.query.pdf === '1'" rel="stylesheet" href="/styles.css" />
    <ClientOnly>
      <SystemAlert
        v-if="alertMessage"
        :message="alertMessage"
        :type="alertType"
        @closed="clearAlert"
        class="fixed top-16 mt-2 right-4 z-50 rounded-lg shadow-md"
      />
      <ConfirmDialog
        :is-visible="isDialogVisible"
        :title="dialogConfig.title"
        :message="dialogConfig.message"
        :confirm-text="dialogConfig.confirmText"
        :cancel-text="dialogConfig.cancelText"
        :type="dialogConfig.type"
        @confirm="handleConfirm"
        @cancel="handleCancel"
      />
    </ClientOnly>
    <NuxtRouteAnnouncer />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup>
import { eventBus } from '~/eventBus'
import SystemAlert from '~/components/SystemAlert.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import { useConfirmDialog } from '~/composables/useConfirmDialog'
import { ClientOnly } from '#components'

const alertMessage = computed(() => eventBus.alertMessage)
const alertType = computed(() => eventBus.alertType)
function clearAlert() {
  eventBus.clearAlert()
}

const { isDialogVisible, dialogConfig, handleConfirm, handleCancel } = useConfirmDialog()
</script>
