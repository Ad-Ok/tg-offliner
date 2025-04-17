import os
from config import OUTPUT_DIR
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.utils import pack_bot_file_id

def process_media(media, client):
    """
    Обрабатывает медиафайлы сообщения и возвращает информацию о них.
    :param media: Объект медиа из сообщения.
    :param client: Экземпляр TelegramClient.
    :return: Словарь с информацией о медиа.
    """
    if isinstance(media, MessageMediaPhoto):
        # Обработка фото
        file_path = client.download_media(media, file="media/")
        return {"type": "photo", "file_path": file_path}

    elif isinstance(media, MessageMediaDocument):
        # Обработка документов (включая видео, аудио и т.д.)
        file_path = client.download_media(media, file="media/")
        return {"type": "document", "file_path": file_path, "mime_type": media.document.mime_type}

    else:
        # Неизвестный тип медиа
        return {"type": "unknown", "info": str(media)}