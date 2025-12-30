<template>
  <div :data-mode="currentMode">
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
import SystemAlert from '~/components/system/SystemAlert.vue'
import ConfirmDialog from '~/components/system/ConfirmDialog.vue'
import { useConfirmDialog } from '~/composables/useConfirmDialog'
import { useDisplayMode } from '~/composables/useDisplayMode'
import { ClientOnly } from '#components'

const { currentMode } = useDisplayMode()

const alertMessage = computed(() => eventBus.alertMessage)
const alertType = computed(() => eventBus.alertType)
function clearAlert() {
  eventBus.clearAlert()
}

const { isDialogVisible, dialogConfig, handleConfirm, handleCancel } = useConfirmDialog()
</script>
