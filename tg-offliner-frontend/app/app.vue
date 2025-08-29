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
import { ClientOnly } from '#components'

const alertMessage = computed(() => eventBus.alertMessage)
const alertType = computed(() => eventBus.alertType)
function clearAlert() {
  eventBus.clearAlert()
}
</script>
