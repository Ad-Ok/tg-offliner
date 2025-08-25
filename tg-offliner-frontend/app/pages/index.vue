<template>
  <ClientOnly>
    <ChannelsList />
  </ClientOnly>
</template>

<script setup>
import ChannelsList from '~/components/ChannelsList.vue'

// Явно указываем использование default layout
definePageMeta({
  layout: 'default'
})
</script>