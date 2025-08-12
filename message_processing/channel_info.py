from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.channels import GetFullChannelRequest
from message_processing.author import download_avatar
import pprint
import os

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
        
        # Выводим в консоль всю информацию о канале
        print("=== entity ===")
        pprint.pprint(entity.to_dict() if hasattr(entity, "to_dict") else entity)
        print("=== full_info ===")
        pprint.pprint(full_info.to_dict() if hasattr(full_info, "to_dict") else full_info)
        
        participants_count = full_info.full_chat.participants_count

        # Получи путь к папке канала
        channel_folder = os.path.join(output_dir, entity.username or str(entity.id))
        os.makedirs(channel_folder, exist_ok=True)

        # Сохрани аватар с правильным аргументом
        avatar_path = download_avatar(entity, client, channel_folder)

        # Получаем количество постов в канале
        try:
            # Получаем первое сообщение, чтобы узнать общее количество
            messages = client.get_messages(entity, limit=1)
            posts_count = messages.total if hasattr(messages, 'total') else 0
            print(f"=== Количество постов в канале: {posts_count} ===")
        except Exception as e:
            print(f"Ошибка при получении количества постов: {e}")
            posts_count = 0

        # Формируем информацию о канале
        return {
            "id": entity.username or str(entity.id),
            "name": entity.title,
            "tagline": "Информация о канале",
            "avatar": avatar_path if avatar_path else "static/default_avatar.png",
            "username": entity.username if entity.username else "Unknown",
            "creation_date": entity.date.strftime('%d %B %Y') if getattr(entity, "date", None) else None,
            "subscribers": participants_count if participants_count is not None else "Unknown",
            "description": getattr(full_info.full_chat, "about", None),
            "posts_count": posts_count
        }

    elif isinstance(entity, User):
        # Получи путь к папке пользователя
        user_folder = os.path.join(output_dir, entity.username or str(entity.id))
        os.makedirs(user_folder, exist_ok=True)

        # Сохраняем аватар пользователя
        avatar_path = download_avatar(entity, client, user_folder)

        # Получаем количество сообщений в переписке с пользователем
        try:
            messages = client.get_messages(entity, limit=1)
            posts_count = messages.total if hasattr(messages, 'total') else 0
            print(f"=== Количество сообщений с пользователем: {posts_count} ===")
        except Exception as e:
            print(f"Ошибка при получении количества сообщений: {e}")
            posts_count = 0

        # Формируем информацию о пользователе
        return {
            "id": entity.username or str(entity.id),
            "name": f"{entity.first_name} {entity.last_name or ''}".strip(),
            "tagline": "Чат с пользователем",
            "avatar": avatar_path if avatar_path else "static/default_avatar.png",
            "username": entity.username if entity.username else "Unknown",
            "creation_date": None,
            "subscribers": None,
            "description": f"Переписка с пользователем {entity.first_name}",
            "posts_count": posts_count
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