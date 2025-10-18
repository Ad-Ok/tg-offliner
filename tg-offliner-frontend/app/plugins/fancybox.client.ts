import { Fancybox } from "@fancyapps/ui";
import "@fancyapps/ui/dist/fancybox/fancybox.css";

export default defineNuxtPlugin(() => {
  // Инициализируем Fancybox для всех элементов с data-fancybox
  // Все изображения канала будут в одной галерее с именем "channel-gallery"
  Fancybox.bind("[data-fancybox]", {
    // Базовые настройки
  } as any);
});
