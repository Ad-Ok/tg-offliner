"""
Утилиты для проверки типов Telegram entities
"""
from telethon.tl.types import Channel, Chat, User
import logging


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
