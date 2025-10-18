<template>
  <div
    v-if="visible"
    :class="['alert', `alert-${type}`]"
    class="system-alert"
    role="alert"
  >
    <span v-html="message"></span>
    <button type="button" class="close" @click="closeAlert">
      <span aria-hidden="true">&times;</span>
    </button>
  </div>
</template>

<script>
export default {
  name: "SystemAlert",
  props: {
    message: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      default: "info",
    },
  },
  data() {
    return {
      visible: true,
    };
  },
  methods: {
    closeAlert() {
      this.visible = false;
      this.$emit("closed");
    },
  },
};
</script>
