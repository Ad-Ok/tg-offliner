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
import shutil
import os

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

def clear_downloads(channel_name):
    """
    Очищает папку текущего канала в downloads, но не удаляет саму папку downloads.
    """
    channel_folder = os.path.join(DOWNLOADS_DIR, channel_name)
    if os.path.exists(channel_folder):
        shutil.rmtree(channel_folder)  # Удаляем папку канала со всем содержимым
        print(f"Папка {channel_folder} очищена.")
    os.makedirs(channel_folder, exist_ok=True)  # Создаём пустую папку

def get_channel_folder(channel_name):
    """
    Возвращает путь к папке для конкретного канала.
    """
    channel_folder = os.path.join(DOWNLOADS_DIR, channel_name)
    os.makedirs(channel_folder, exist_ok=True)  # Создаём папку канала, если её нет

    # Создаём папку media внутри папки канала
    media_folder = os.path.join(channel_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    return channel_folder

def main(channel_username=None):
    # Очищаем папку текущего канала
    clear_downloads(channel_username)

    start_time = time.time()

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

    replace_all = None  # Флаг для "да для всех"

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

        # Проверяем, существует ли пост в базе
        try:
            response = requests.get(f"http://127.0.0.1:5000/api/posts/check?telegram_id={post.id}&channel_id={channel_username}")
            if response.status_code == 200:
                response_data = response.json()
                # Проверяем, что ответ содержит ключ "exists"
                if isinstance(response_data, dict) and response_data.get("exists"):
                    print(f"Пост с ID {post.id} из канала {channel_username} уже существует в базе.")
                    
                    # Если пользователь уже выбрал "да для всех"
                    if replace_all is True:
                        print(f"Заменяем пост с ID {post.id}.")
                    elif replace_all is False:
                        print(f"Пропускаем пост с ID {post.id}.")
                        continue  # Пропускаем обработку текущего поста
                    else:
                        # Диалог с пользователем
                        user_input = input("Пост уже существует. Хотите его заменить? (y/n/a): ").strip().lower()
                        if user_input == "y":
                            print(f"Заменяем пост с ID {post.id}.")
                        elif user_input == "n":
                            print(f"Пропускаем пост с ID {post.id}.")
                            continue  # Пропускаем обработку текущего поста
                        elif user_input == "a":
                            print("Выбрано 'да для всех'. Все существующие посты будут заменены.")
                            replace_all = True
                        else:
                            print("Неверный ввод. Пропускаем пост.")
                            continue
                else:
                    print(f"Неожиданный формат ответа от API: {response_data}")
            else:
                print(f"Ошибка при проверке существования поста: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка при проверке существования поста: {e}")
            continue

        # Преобразуем текст и entities в HTML
        formatted_message = parse_entities_to_html(post.message or "", post.entities or "")

        # Обрабатываем опрос, если он есть
        if post.poll:
            poll_html = process_poll(post)
            formatted_message += f"<br>{poll_html}"

        # Получаем папку для текущего канала
        channel_folder = get_channel_folder(channel_username)

        # Скачиваем медиа
        media_path = None
        media_type = None
        mime_type = None

        if post.media and not post.poll:  # Пропускаем скачивание медиа для опросов
            media_path = client.download_media(
                post.media,
                file=os.path.join(channel_folder, "media", f"{post.id}_media")
            )
            media_type = type(post.media).__name__  # Тип медиа (например, MessageMediaPhoto)
            if isinstance(post.media, MessageMediaDocument) and isinstance(post.media.document, Document):
                mime_type = getattr(post.media.document, 'mime_type', None)

            # Сохраняем относительный путь
            if media_path:
                media_path = os.path.relpath(media_path, DOWNLOADS_DIR)  # Относительный путь от папки downloads

        # Обрабатываем автора сообщения
        sender_name, sender_avatar, sender_link = process_author(post.sender, client, channel_folder, peer_id=post.peer_id, from_id=post.from_id)

        # Обрабатываем автора репоста, если это репост
        repost_name, repost_avatar, repost_link = None, None, None
        if post.fwd_from and post.fwd_from.from_id:
            try:
                repost_entity = client.get_entity(post.fwd_from.from_id)  # Получаем полную информацию об авторе репоста
                repost_name, repost_avatar, repost_link = process_author(repost_entity, client, channel_folder)
            except Exception as e:
                print(f"Ошибка при обработке автора репоста: {e}")

        # Обрабатываем реакции
        reactions = None
        if post.reactions and post.reactions.results:
            reactions = {
                "total_count": sum(r.count for r in post.reactions.results),  # Суммируем количество всех реакций
                "recent_reactions": [
                    {"reaction": str(r.reaction), "count": r.count} for r in post.reactions.results
                ]
            }

        # Сохраняем данные в базу
        api_data = {
            "telegram_id": post.id,
            "channel_id": channel_username,  # Добавляем ID или имя канала
            "date": post.date.strftime('%Y-%m-%dT%H:%M:%S'),
            "message": formatted_message,
            "media_url": media_path,
            "media_type": media_type,
            "mime_type": mime_type,
            "author_name": sender_name,
            "author_avatar": sender_avatar,
            "author_link": sender_link,
            "repost_author_name": repost_name,
            "repost_author_avatar": repost_avatar,
            "repost_author_link": repost_link,
            "reactions": reactions  # Добавляем реакции
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