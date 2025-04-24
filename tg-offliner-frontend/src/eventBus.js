import { reactive } from "vue";

export const eventBus = reactive({
  alertMessage: "",
  alertType: "info",
  showAlert(message, type = "info") {
    this.alertMessage = message;
    this.alertType = type;
  },
  clearAlert() {
    this.alertMessage = "";
    this.alertType = "info";
  },
});