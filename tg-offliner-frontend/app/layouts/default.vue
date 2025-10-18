<template>
  <div class="min-h-screen bg-base-200">
    <Navbar />
    <main class="container mx-auto pt-24 p-4 pb-8">
      <slot />
    </main>
  </div>
</template>

<script setup>
import Navbar from '~/components/system/Navbar.vue'
</script>
