from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.channels import GetFullChannelRequest
from message_processing.author import download_avatar
import pprint
import os

def get_discussion_group(client, full_info):
    """
    Получает ID группы обсуждений канала, если она есть.
    """
    try:
        if hasattr(full_info, 'full_chat') and hasattr(full_info.full_chat, 'linked_chat_id'):
            linked_chat_id = full_info.full_chat.linked_chat_id
            if linked_chat_id:
                print(f"=== Найдена группа обсуждений с ID: {linked_chat_id} ===")
                return linked_chat_id
                    
    except Exception as e:
        print(f"Ошибка при получении группы обсуждений: {e}")
    
    return None

def get_channel_info(client, entity, output_dir, folder_name=None):
    """
    Формирует информацию о канале, пользователе или чате.

    :param client: Подключённый клиент Telethon.
    :param entity: Объект канала, пользователя или чата.
    :param output_dir: Папка для сохранения аватара.
    :param folder_name: Имя папки для сохранения (если None, генерируется автоматически).
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

        # Получаем группу обсуждений канала, если она есть
        discussion_group_id = get_discussion_group(client, full_info)

        # Получи путь к папке канала
        if folder_name is None:
            folder_name = entity.username or f"channel_{entity.id}"
        channel_folder = os.path.join(output_dir, folder_name)
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

        # Получаем количество комментариев из группы обсуждений
        comments_count = 0
        if discussion_group_id:
            try:
                from utils.entity_validation import get_entity_by_username_or_id
                discussion_entity, error = get_entity_by_username_or_id(client, str(discussion_group_id))
                if discussion_entity:
                    discussion_messages = client.get_messages(discussion_entity, limit=1)
                    comments_count = discussion_messages.total if hasattr(discussion_messages, 'total') else 0
                    print(f"=== Количество сообщений в группе обсуждений: {comments_count} ===")
            except Exception as e:
                print(f"Ошибка при получении количества комментариев: {e}")

        # Формируем информацию о канале
        channel_id = entity.username or str(entity.id)
        return {
            "id": channel_id,
            "name": entity.title,
            "tagline": "Информация о канале",
            "avatar": avatar_path if avatar_path else None,
            "username": entity.username if entity.username else f"channel_{entity.id}",
            "creation_date": entity.date.strftime('%d %B %Y') if getattr(entity, "date", None) else None,
            "subscribers": participants_count if participants_count is not None else None,
            "description": getattr(full_info.full_chat, "about", None),
            "posts_count": posts_count,
            "comments_count": comments_count,  # Добавляем количество комментариев
            "discussion_group_id": discussion_group_id  # Добавляем ID группы обсуждений
        }

    elif isinstance(entity, User):
        # Получи путь к папке пользователя
        if folder_name is None:
            folder_name = entity.username or f"user_{entity.id}"
        user_folder = os.path.join(output_dir, folder_name)
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
        user_id = entity.username or str(entity.id)
        return {
            "id": user_id,
            "name": f"{entity.first_name} {entity.last_name or ''}".strip(),
            "tagline": "Чат с пользователем", 
            "avatar": avatar_path if avatar_path else None,
            "username": entity.username if entity.username else f"user_{entity.id}",
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