<template>
  <div>
    <ClientOnly>
      <SystemAlert
        v-if="alertMessage"
        :message="alertMessage"
        :type="alertType"
        @closed="clearAlert"
      />
    </ClientOnly>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </div>
</template>

<script setup>
import { eventBus } from '~/eventBus'
import SystemAlert from '~/components/SystemAlert.vue'
import { ClientOnly } from '#components'

const alertMessage = computed(() => eventBus.alertMessage)
const alertType = computed(() => eventBus.alertType)
function clearAlert() {
  eventBus.clearAlert()
}
</script>
