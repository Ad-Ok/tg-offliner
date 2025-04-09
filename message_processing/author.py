import os
from config import OUTPUT_DIR

def process_author(sender, client, peer_id=None):
    """Обрабатывает автора сообщения."""
    sender_name = ""
    sender_avatar = ""
    sender_link = ""

    if sender:
        if hasattr(sender, 'first_name') or hasattr(sender, 'last_name'):  # Пользователь
            sender_name = sender.first_name or sender.last_name or "Без имени"
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/user?id={sender.id}"
        elif hasattr(sender, 'title'):  # Канал
            sender_name = sender.title
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"

        # Скачивание аватара
        avatar_dir = os.path.join(OUTPUT_DIR, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        if sender.photo:
            avatar_path = client.download_profile_photo(
                sender,
                file=os.path.join(avatar_dir, f"avatar_{sender.id}.jpg")
            )
            sender_avatar = f"avatars/{os.path.basename(avatar_path)}" if avatar_path else ""

    # Если sender отсутствует, используем peer_id
    elif peer_id:
        # Получаем информацию о чате
        chat = client.get_entity(peer_id)
        sender_name = chat.title
        if chat.username:
            sender_link = f"https://t.me/{chat.username}"
        elif chat.id:
            sender_link = f"https://t.me/c/{chat.id}"

        # Скачивание аватара чата
        avatar_dir = os.path.join(OUTPUT_DIR, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        if chat.photo:
            avatar_path = client.download_profile_photo(
                chat,
                file=os.path.join(avatar_dir, f"avatar_{chat.id}.jpg")
            )
            sender_avatar = f"avatars/{os.path.basename(avatar_path)}" if avatar_path else ""

    return sender_name, sender_avatar, sender_link