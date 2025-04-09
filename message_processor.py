import os
from telethon.utils import html
from config import OUTPUT_DIR  # Импортируем OUTPUT_DIR из config.py

def filter_messages(messages, channel_username, client):
    """Фильтрует сообщения, оставляя только репосты из указанного канала."""
    filtered = []
    for message in messages:
        if not message.message and not message.media:
            continue

        if message.fwd_from:
            if message.fwd_from.from_id:
                source_entity = client.get_entity(message.fwd_from.from_id)
                if hasattr(source_entity, 'username') and source_entity.username == channel_username:
                    filtered.append(message)
            elif message.fwd_from.from_name == channel_username:
                filtered.append(message)

    return filtered

def process_message(message, client):
    """Обрабатывает одно сообщение и возвращает данные для HTML."""
    # Обработка автора сообщения
    sender = message.sender
    sender_name = ""
    sender_avatar = ""
    sender_link = ""

    if sender:
        if hasattr(sender, 'first_name') or hasattr(sender, 'last_name'):  # Если это пользователь
            # Имя автора
            sender_name = sender.first_name or sender.last_name or "Без имени"

            # Ссылка на профиль
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/user?id={sender.id}"

        elif hasattr(sender, 'title'):  # Если это канал
            # Название канала
            sender_name = sender.title

            # Ссылка на канал
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"

        # Скачивание аватара
        avatar_dir = os.path.join(OUTPUT_DIR, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        avatar_path = client.download_profile_photo(
            sender,
            file=os.path.join(avatar_dir, f"avatar_{sender.id}.jpg")
        )
        if avatar_path:
            sender_avatar = f"avatars/{os.path.basename(avatar_path)}"

    # Обработка текста сообщения
    formatted_text = html.unparse(message.message, message.entities) if message.message else ""

    # Обработка медиа
    media_html = ""
    media_dir = os.path.join(OUTPUT_DIR, "media")
    os.makedirs(media_dir, exist_ok=True)

    if message.media:
        media_path = client.download_media(
            message,
            file=os.path.join(media_dir, f"media_{message.id}")
        )
        if media_path:
            if media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                media_html = f'<img src="media/{os.path.basename(media_path)}" alt="Media" class="media">'
            elif media_path.lower().endswith(('.mp4', '.webm')):
                media_html = f'<video controls class="media"><source src="media/{os.path.basename(media_path)}" type="video/mp4">Ваш браузер не поддерживает видео.</video>'
            else:
                media_html = f'<a href="media/{os.path.basename(media_path)}" download>Скачать файл</a>'

    return {
        "sender_name": sender_name,
        "sender_avatar": sender_avatar,
        "sender_link": sender_link,
        "formatted_text": formatted_text,
        "media_html": media_html,
        "reactions_html": "",
        "reply_html": "",
        "repost_html": "",
    }