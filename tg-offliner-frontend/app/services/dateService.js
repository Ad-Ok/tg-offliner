export function formatMessageDate(messageDate) {
    if (!messageDate) {
      return "Неизвестно";
    }
  
    const months = {
      1: "января",
      2: "февраля",
      3: "марта",
      4: "апреля",
      5: "мая",
      6: "июня",
      7: "июля",
      8: "августа",
      9: "сентября",
      10: "октября",
      11: "ноября",
      12: "декабря",
    };
  
    const date = new Date(messageDate);
  
    // Форматируем дату
    const day = date.getDate();
    const month = months[date.getMonth() + 1]; // Месяцы в JavaScript начинаются с 0
    const year = date.getFullYear();
    const time = date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    });
  
    return `${day} ${month} ${year} ${time}`;
  }