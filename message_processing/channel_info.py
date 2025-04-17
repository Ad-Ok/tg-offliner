from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.channels import GetFullChannelRequest
from message_processing.author import download_avatar

def get_channel_info(client, entity, output_dir):
    """
    Формирует информацию о канале, пользователе или чате.

    :param client: Подключённый клиент Telethon.
    :param entity: Объект канала, пользователя или чата.
    :param output_dir: Папка для сохранения аватара.
    :return: Словарь с информацией о канале, пользователе или чате.
    """
    if isinstance(entity, Channel):
        # Получаем полную информацию о канале
        full_info = client(GetFullChannelRequest(channel=entity))
        participants_count = full_info.full_chat.participants_count

        # Сохраняем аватар канала
        avatar_path = download_avatar(entity, client)

        # Формируем информацию о канале
        return {
            "name": entity.title,
            "tagline": "Информация о канале",
            "avatar": avatar_path if avatar_path else "static/default_avatar.png",
            "username": entity.username if entity.username else "Unknown",
            "creation_date": entity.date.strftime('%d %B %Y'),
            "subscribers": participants_count if participants_count is not None else "Unknown"
        }

    elif isinstance(entity, User):
        # Сохраняем аватар пользователя
        avatar_path = download_avatar(entity, client)

        # Формируем информацию о пользователе
        return {
            "name": f"{entity.first_name} {entity.last_name or ''}".strip(),
            "tagline": "Чат с пользователем",
            "avatar": avatar_path if avatar_path else "static/default_avatar.png",
            "username": entity.username if entity.username else "Unknown",
            "creation_date": "Unknown",
            "subscribers": "N/A"
        }

    elif isinstance(entity, Chat):
        # Сохраняем аватар чата
        avatar_path = download_avatar(entity, client)

        # Формируем информацию о чате
        return {
            "name": entity.title,
            "tagline": "Групповой чат",
            "avatar": avatar_path if avatar_path else "static/default_avatar.png",
            "username": "Unknown",
            "creation_date": "Unknown",
            "subscribers": "N/A"
        }

    else:
        raise ValueError("Неизвестный тип объекта. Экспорт невозможен.")