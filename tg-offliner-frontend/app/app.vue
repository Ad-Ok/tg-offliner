<template>
  <div class="min-h-screen bg-gray-100">
    <link v-if="$route.query.pdf === '1'" rel="stylesheet" href="/pdf.css" />
    <ClientOnly>
      <SystemAlert
        v-if="alertMessage"
        :message="alertMessage"
        :type="alertType"
        @closed="clearAlert"
        class="rounded-lg shadow-md"
      />
    </ClientOnly>
    <NuxtRouteAnnouncer />
    <NuxtPage class="container mx-auto px-4 py-8" />
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
