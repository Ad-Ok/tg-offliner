def format_elapsed_time(elapsed_time):
    """Форматирует время выполнения в строку."""
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} ч.")
    if minutes > 0 or hours > 0:  # Показываем минуты, если есть часы
        time_parts.append(f"{minutes} мин.")
    time_parts.append(f"{seconds} сек.")

    return " ".join(time_parts)