from telethon.sync import TelegramClient
from config import EXPORT_SETTINGS
from telegram_client import connect_to_telegram
import time
import argparse
import requests
from utils.text_format import parse_entities_to_html
import os
from message_processing.polls import process_poll
from telethon.tl.types import DocumentAttributeFilename, Document, MessageMediaDocument
from message_processing.author import process_author

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
MEDIA_DIR = os.path.join(DOWNLOADS_DIR, 'media')
os.makedirs(MEDIA_DIR, exist_ok=True)  # Создаём папку, если её нет

def main(channel_username=None):
    start_time = time.time()

    # Очистка базы данных перед началом скачивания
    try:
        response = requests.delete("http://127.0.0.1:5000/api/posts")
        if response.status_code == 200:
            print(response.json()["message"])
        else:
            print(f"Ошибка при очистке базы данных: {response.text}")
    except Exception as e:
        print(f"Ошибка при подключении к API для очистки базы данных: {e}")
        return

    # Подключение к Telegram
    client = connect_to_telegram()
    entity = client.get_entity(channel_username)

    # Применяем параметры из EXPORT_SETTINGS
    include_system_messages = EXPORT_SETTINGS.get("include_system_messages", False)
    include_reposts = EXPORT_SETTINGS.get("include_reposts", True)
    include_polls = EXPORT_SETTINGS.get("include_polls", True)
    message_limit = EXPORT_SETTINGS.get("message_limit", None)

    # Получение списка сообщений
    all_posts = client.iter_messages(
        entity,
        limit=message_limit,
        reverse=True  # Обходим от старых к новым
    )
    processed_count = 0

    for post in all_posts:
        # Пропускаем системные сообщения, если они отключены
        if not include_system_messages and post.action:
            print(f"Пропущено системное сообщение с ID {post.id}")
            continue

        # Пропускаем репосты, если они отключены
        if not include_reposts and post.fwd_from:
            continue

        # Пропускаем опросы, если они отключены
        if not include_polls and post.poll:
            continue

        # Преобразуем текст и entities в HTML
        formatted_message = parse_entities_to_html(post.message or "", post.entities or "")

        # Обрабатываем опрос, если он есть
        if post.poll:
            poll_html = process_poll(post)
            formatted_message += f"<br>{poll_html}"

        # Скачиваем медиа, если оно есть
        media_path = None
        media_type = None
        mime_type = None
        if post.media and not post.poll:  # Пропускаем скачивание медиа для опросов
            media_path = client.download_media(post.media, file=os.path.join(MEDIA_DIR, f"{post.id}_media"))
            media_type = type(post.media).__name__  # Тип медиа (например, MessageMediaPhoto)
            if isinstance(post.media, MessageMediaDocument) and isinstance(post.media.document, Document):
                mime_type = getattr(post.media.document, 'mime_type', None)

            # Сохраняем относительный путь
            if media_path:
                media_path = os.path.relpath(media_path, DOWNLOADS_DIR)  # Относительный путь от папки downloads

        # Обрабатываем автора сообщения
        sender_name, sender_avatar, sender_link = process_author(post.sender, client, peer_id=post.peer_id, from_id=post.from_id)

        # Сохраняем ID, дату, текст сообщения, ссылку на медиа, его тип, MIME-тип, автора и аватар
        api_data = {
            "telegram_id": post.id,
            "date": post.date.strftime('%Y-%m-%dT%H:%M:%S'),  # Преобразуем дату в строку
            "message": formatted_message,  # Сохраняем отформатированный текст
            "media_url": media_path,  # Относительный путь
            "media_type": media_type,
            "mime_type": mime_type,  # Добавляем MIME-тип
            "author_name": sender_name,  # Имя автора
            "author_avatar": sender_avatar,  # Ссылка на аватар
            "author_link": sender_link  # Ссылка на автора
        }
        print("Отправляемые данные:", api_data)
        try:
            response = requests.post("http://127.0.0.1:5000/api/posts", json=api_data)
            if response.status_code == 201:
                print(f"Пост {post.id} успешно добавлен в базу данных.")
            else:
                print(f"Ошибка при добавлении поста {post.id}: {response.text}")
        except Exception as e:
            print(f"Ошибка при подключении к API: {e}")

        processed_count += 1

    client.disconnect()

    elapsed_time = time.time() - start_time
    print(f"Экспорт завершён за {elapsed_time:.2f} секунд.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Экспорт постов Telegram в базу данных.")
    parser.add_argument(
        "--channel",
        required=True,
        help="Имя Telegram-канала (без @), из которого нужно экспортировать посты."
    )
    args = parser.parse_args()

    # Передаём имя канала из аргументов
    channel_username = args.channel

    main(channel_username=channel_username)