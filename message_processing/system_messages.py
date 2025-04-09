def process_system_message(message):
    """Обрабатывает системное сообщение."""
    if message.action:
        return f"Системное сообщение: {type(message.action).__name__}"
    return None