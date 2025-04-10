from datetime import datetime

def format_message_date(message_date):
    """Форматирует дату сообщения в виде '9 апреля 2025 22:47'."""
    if not message_date:
        return "Неизвестно"

    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
        7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    return f"{message_date.day} {months[message_date.month]} {message_date.year} {message_date.strftime('%H:%M')}"