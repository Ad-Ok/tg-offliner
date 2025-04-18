from config import DOWNLOADS_DIR
import os

def download_avatar(entity, client):
    """
    Скачивает аватар для указанного объекта (пользователь, чат или канал).
    :param entity: Объект (пользователь, чат или канал), для которого нужно скачать аватар.
    :param client: Экземпляр TelegramClient.
    :return: Относительный путь к сохранённому аватару или пустая строка, если аватар отсутствует.
    """
    avatar_dir = os.path.join(DOWNLOADS_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)  # Создаём папку, если её нет

    if entity and entity.photo:  # Проверяем, есть ли фото у объекта
        try:
            avatar_path = client.download_profile_photo(
                entity,
                file=os.path.join(avatar_dir, f"avatar_{entity.id}.jpg")
            )
            if avatar_path:
                print(f"Аватар сохранён: {avatar_path}")
                return f"avatars/{os.path.basename(avatar_path)}"  # Возвращаем относительный путь
        except Exception as e:
            print(f"Ошибка при скачивании аватара: {e}")
    return ""

def process_author(sender, client, peer_id=None, from_id=None):
    """Обрабатывает автора сообщения или оригинального поста из репоста."""
    sender_name = ""
    sender_avatar = ""
    sender_link = ""

    # Если передан sender (автор сообщения)
    if sender:
        if hasattr(sender, 'first_name') or hasattr(sender, 'last_name'):  # Пользователь
            sender_name = sender.first_name or sender.last_name or "Без имени"
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/user?id={sender.id}"
        elif hasattr(sender, 'title'):  # Канал или группа
            sender_name = sender.title
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"

        sender_avatar = download_avatar(sender, client)

    # Если sender отсутствует, но есть peer_id (например, для чата)
    elif peer_id:
        # Получаем информацию о чате
        chat = client.get_entity(peer_id)
        sender_name = chat.title
        if chat.username:
            sender_link = f"https://t.me/{chat.username}"
        elif chat.id:
            sender_link = f"https://t.me/c/{chat.id}"

        sender_avatar = download_avatar(chat, client)

    # Если передан from_id (например, для автора оригинального поста из репоста)
    elif from_id:
        try:
            entity = client.get_entity(from_id)
            if hasattr(entity, 'first_name') or hasattr(entity, 'last_name'):  # Пользователь
                sender_name = entity.first_name or entity.last_name or "Без имени"
                if entity.username:
                    sender_link = f"https://t.me/{entity.username}"
                elif entity.id:
                    sender_link = f"https://t.me/user?id={entity.id}"
            elif hasattr(entity, 'title'):  # Канал или группа
                sender_name = entity.title
                if entity.username:
                    sender_link = f"https://t.me/{entity.username}"
                elif entity.id:
                    sender_link = f"https://t.me/c/{entity.id}"

            sender_avatar = download_avatar(entity, client)
        except Exception as e:
            print(f"Ошибка при получении информации об авторе: {e}")

    return sender_name, sender_avatar, sender_link