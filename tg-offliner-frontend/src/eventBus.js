import { reactive } from "vue";

export const DEFAULT_AUTO_CLOSE_TIME = 5000;

export const eventBus = reactive({
  alertMessage: "",
  alertType: "info",
  autoClose: DEFAULT_AUTO_CLOSE_TIME,
  showAlert(message, type = "info", autoClose) {
    this.alertMessage = message;
    this.alertType = type;
    this.autoClose = autoClose !== undefined ? autoClose : DEFAULT_AUTO_CLOSE_TIME;
  },
  clearAlert() {
    this.alertMessage = "";
    this.alertType = "info";
    this.autoClose = DEFAULT_AUTO_CLOSE_TIME;
  },
});