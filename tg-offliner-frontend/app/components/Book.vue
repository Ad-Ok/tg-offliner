<template>
  <ClientOnly v-if="loading">
    <div class="loading">Загрузка...</div>
  </ClientOnly>
  <div v-else>
    <div v-for="page in pages" :key="page.id" class="mb-6">
      <Page :page="page" />
    </div>
  </div>
</template>

<script>
import Page from './Page.vue';

export default {
  name: "Book",
  components: { Page },
  props: {
    channelId: { type: String, required: true },
    pages: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false }
  }
}
</script>

<style scoped>
/* Стили для компонента Book - пока пустые */
</style>