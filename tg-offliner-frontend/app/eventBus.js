import { reactive } from "vue";

export const eventBus = reactive({
  alertMessage: "",
  alertType: "info",
  alertOptions: {},
  
  showAlert(message, type = "info", options = {}) {
    this.alertMessage = message;
    this.alertType = type;
    this.alertOptions = options;
  },
  
  clearAlert() {
    this.alertMessage = "";
    this.alertType = "info";
    this.alertOptions = {};
  }
});