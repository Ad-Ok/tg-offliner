<template>
  <div>
    <h1>Telegram Offliner</h1>
    <!-- Компонент SystemAlert -->
    <SystemAlert
      v-if="alertMessage"
      :message="alertMessage"
      :type="alertType"
      @closed="clearAlert"
    />
    <router-view />
  </div>
</template>

<script>
import { eventBus } from "@/eventBus";
import SystemAlert from "@/components/SystemAlert.vue";

export default {
  name: "App",
  components: {
    SystemAlert,
  },
  computed: {
    alertMessage() {
      return eventBus.alertMessage;
    },
    alertType() {
      return eventBus.alertType;
    },
  },
  methods: {
    clearAlert() {
      eventBus.clearAlert();
    },
  },
};
</script>

<style>
.loading {
  font-size: 18px;
  text-align: center;
  margin-top: 20px;
}

.reactions {
  display: flex;
  margin-top: 10px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 5px;
}

.message {
  margin-bottom: 20px;
}
</style>
