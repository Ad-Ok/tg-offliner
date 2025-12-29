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
  
    // Форматируем дату используя UTC для избежания hydration mismatch
    const day = date.getUTCDate();
    const month = months[date.getUTCMonth() + 1]; // Месяцы в JavaScript начинаются с 0
    const year = date.getUTCFullYear();
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const time = `${hours}:${minutes}`;
  
    return `${day} ${month} ${year} ${time}`;
  }