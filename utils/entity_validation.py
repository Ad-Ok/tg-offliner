"""
Утилиты для проверки типов Telegram entities
"""
from telethon.tl.types import Channel, Chat, User
import logging


def parse_username_or_id(username_or_id):
    """
    Парсит введенную строку и возвращает либо username, либо числовой ID.
    
    Args:
        username_or_id: Строка, которая может быть username (@username, username) или ID (123456789)
        
    Returns:
        tuple: (parsed_value, is_id)
            - parsed_value: обработанное значение (username без @ или int ID)
            - is_id: True если это числовой ID, False если username
    """
    # Удаляем @ если есть
    cleaned = username_or_id.strip().lstrip('@')
    
    # Проверяем, является ли это числом (Peer ID)
    if cleaned.isdigit():
        return int(cleaned), True
    
    # Если начинается с минуса, тоже может быть ID (для каналов/чатов)
    if cleaned.startswith('-') and cleaned[1:].isdigit():
        return int(cleaned), True
    
    # Иначе это username
    return cleaned, False


def validate_entity_for_download(entity, username):
    """
    Проверяет, что entity можно скачать (канал или пользователь).
    
    Args:
        entity: Telegram entity
        username: Имя пользователя/канала для логирования
        
    Returns:
        dict: {"valid": bool, "error": str or None, "type": str}
    """
    
    if isinstance(entity, User):
        logging.info(f"Entity {username} является пользователем - поддерживается для скачивания переписки")
        return {"valid": True, "error": None, "type": "user"}
    
    if isinstance(entity, Chat):
        error_msg = f'@{username} является обычным чатом. Поддерживаются только каналы и пользователи.'
        logging.warning(f"Entity {username} является обычным чатом")
        return {"valid": False, "error": error_msg, "type": "chat"}
    
    if not isinstance(entity, Channel):
        error_msg = f'@{username} имеет неподдерживаемый тип. Поддерживаются только каналы и пользователи.'
        logging.warning(f"Entity {username} имеет неподдерживаемый тип: {type(entity).__name__}")
        return {"valid": False, "error": error_msg, "type": "unknown"}
    
    # Для каналов проверяем, что это публичный канал
    if not entity.broadcast:
        error_msg = f'@{username} не является публичным каналом. Поддерживаются только публичные каналы.'
        logging.warning(f"Entity {username} не является публичным каналом (broadcast=False)")
        return {"valid": False, "error": error_msg, "type": "private_channel"}
    
    logging.info(f"Entity {username} прошла валидацию как публичный канал")
    return {"valid": True, "error": None, "type": "channel"}


def get_entity_by_username_or_id(client, username_or_id):
    """
    Получает Telegram entity по username или ID.
    
    Args:
        client: Telethon клиент
        username_or_id: Username (@username, username) или числовой ID
        
    Returns:
        tuple: (entity, error_message)
            - entity: Telegram entity или None в случае ошибки
            - error_message: сообщение об ошибке или None в случае успеха
    """
    try:
        parsed_value, is_id = parse_username_or_id(username_or_id)
        
        if is_id:
            logging.info(f"Попытка получить entity по ID: {parsed_value}")
            entity = client.get_entity(parsed_value)
        else:
            logging.info(f"Попытка получить entity по username: {parsed_value}")
            entity = client.get_entity(parsed_value)
            
        return entity, None
        
    except ValueError as e:
        error_msg = f"Не удалось найти пользователя/канал '{username_or_id}'. Проверьте правильность ввода."
        logging.warning(f"ValueError при получении entity для {username_or_id}: {str(e)}")
        return None, error_msg
        
    except Exception as e:
        error_msg = f"Ошибка при поиске '{username_or_id}': {str(e)}"
        logging.error(f"Неожиданная ошибка при получении entity для {username_or_id}: {str(e)}")
        return None, error_msg
