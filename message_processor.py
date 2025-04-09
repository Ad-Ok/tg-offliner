import os
from telethon.utils import html
from config import OUTPUT_DIR  # Импортируем OUTPUT_DIR из config.py

def process_message(message, client):
    """Обрабатывает одно сообщение и возвращает данные для HTML."""
    # Обработка автора сообщения
    sender = message.sender
    sender_name = ""
    sender_avatar = ""
    sender_link = ""

    if sender:
        if hasattr(sender, 'first_name') or hasattr(sender, 'last_name'):  # Если это пользователь
            sender_name = sender.first_name or sender.last_name or "Без имени"
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/user?id={sender.id}"
        elif hasattr(sender, 'title'):  # Если это канал
            sender_name = sender.title
            if sender.username:
                sender_link = f"https://t.me/{sender.username}"
            elif sender.id:
                sender_link = f"https://t.me/c/{sender.id}"

    # Скачивание аватара
    avatar_dir = os.path.join(OUTPUT_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    if sender and sender.photo:
        avatar_path = client.download_profile_photo(
            sender,
            file=os.path.join(avatar_dir, f"avatar_{sender.id}.jpg")
        )
        sender_avatar = f"avatars/{os.path.basename(avatar_path)}" if avatar_path else ""

# Проверка на системное сообщение
    if message.action:
        system_message = f"Системное сообщение: {type(message.action).__name__}"
        return {
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "sender_link": sender_link,
            "formatted_text": system_message,
            "media_html": "",
            "reactions_html": "",
            "reply_html": "",
            "repost_html": "",
        }

    # Обработка текста сообщения
    formatted_text = html.unparse(message.message, message.entities) if message.message else ""

    # Обработка голосования
    poll_html = ""
    if message.poll and message.poll.poll:  # Проверяем, что это голосование
        poll_question = message.poll.poll.question.text if hasattr(message.poll.poll.question, 'text') else str(message.poll.poll.question)
        poll_answers = message.poll.poll.answers
        poll_results = message.poll.results.results if message.poll.results else []

        poll_html = f"<h3>Голосование: {poll_question}</h3><ul>"
        for i, answer in enumerate(poll_answers):
            # Извлекаем текст ответа
            answer_text = answer.text.text if hasattr(answer.text, 'text') else str(answer.text)
            votes = poll_results[i].voters if poll_results else "?"
            poll_html += f"<li>{answer_text} — {votes} голосов</li>"
        poll_html += "</ul>"

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
        "poll_html": poll_html,
        "media_html": media_html,
        "reactions_html": "",
        "reply_html": "",
        "repost_html": "",
    }