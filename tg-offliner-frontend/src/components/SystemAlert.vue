<template>
  <div
    v-if="visible"
    :class="['alert', `alert-${type}`]"
    class="system-alert"
    role="alert"
  >
    <span>{{ message }}</span>
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
      default: "info", // Тип сообщения: 'success', 'danger', 'warning', 'info'
    },
    autoClose: {
      type: [Boolean, Number], // Либо false, либо число (время в мс)
      default: null, // Значение по умолчанию не задаётся здесь
    },
  },
  data() {
    return {
      visible: true,
    };
  },
  mounted() {
    if (this.autoClose !== false && typeof this.autoClose === "number") {
      setTimeout(this.closeAlert, this.autoClose);
    }
  },
  methods: {
    closeAlert() {
      this.visible = false;
      this.$emit("closed"); // Генерируем событие закрытия
    },
  },
};
</script>

<style>
.system-alert {
  position: relative;
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.alert-info {
  color: #31708f;
  background-color: #d9edf7;
  border-color: #bce8f1;
}

.alert-success {
  color: #3c763d;
  background-color: #dff0d8;
  border-color: #d6e9c6;
}

.alert-warning {
  color: #8a6d3b;
  background-color: #fcf8e3;
  border-color: #faebcc;
}

.alert-danger {
  color: #a94442;
  background-color: #f2dede;
  border-color: #ebccd1;
}

.close {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  color: inherit;
  cursor: pointer;
}
</style>