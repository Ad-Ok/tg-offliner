from config import DOWNLOADS_DIR
import os

def download_avatar(entity, client, channel_folder):
    """
    Скачивает аватар пользователя или канала в папку канала с уникальным именем.
    """
    if entity and entity.photo:
        try:
            # Создаем папку avatars если её нет
            avatars_folder = os.path.join(channel_folder, "avatars")
            os.makedirs(avatars_folder, exist_ok=True)
            
            # Генерируем уникальное имя файла на основе ID
            avatar_filename = f"avatar_{entity.id}.jpg"
            avatar_full_path = os.path.join(avatars_folder, avatar_filename)
            
            avatar_path = client.download_profile_photo(
                entity,
                file=avatar_full_path
            )
            if avatar_path:
                print(f"Аватар сохранён: {avatar_path}")
                # Возвращаем путь относительно DOWNLOADS_DIR
                relative_path = os.path.relpath(avatar_path, DOWNLOADS_DIR)
                return relative_path
        except Exception as e:
            print(f"Ошибка при скачивании аватара: {e}")
    return None

def process_author(sender, client, channel_folder, peer_id=None, from_id=None):
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
            sender_avatar = download_avatar(sender, client, channel_folder)  # Передаём channel_folder
        elif hasattr(sender, 'title'):  # Канал или группа
            sender_name = sender.title
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"
            sender_avatar = download_avatar(sender, client, channel_folder)  # Передаём channel_folder

    return sender_name, sender_avatar, sender_link