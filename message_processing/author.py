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
            sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Без имени"
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/user?id={sender.id}"
            sender_avatar = download_avatar(sender, client)
        elif hasattr(sender, 'title'):  # Канал или группа
            sender_name = sender.title
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"
            sender_avatar = download_avatar(sender, client)

    return sender_name, sender_avatar, sender_link