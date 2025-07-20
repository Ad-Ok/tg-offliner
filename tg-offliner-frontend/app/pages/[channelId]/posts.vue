<template>
  <Wall :channelId="channelId" />
</template>

<script setup>
import { useRoute } from 'vue-router'
import Wall from '~/components/Wall.vue'

const route = useRoute()
const channelId = route.params.channelId
</script>