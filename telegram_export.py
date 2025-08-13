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
import logging
from message_processing.channel_info import get_channel_info

# Настройка логирования
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

def import_channel_direct(channel_username):
    """
    Импортирует канал или переписку с пользователем напрямую, используя существующий клиент.
    Возвращает словарь с результатом.
    """
    try:
        # Используем существующий глобальный клиент
        client = connect_to_telegram()
        
        # Получаем entity по username или ID
        from utils.entity_validation import get_entity_by_username_or_id, validate_entity_for_download
        entity, error_message = get_entity_by_username_or_id(client, channel_username)
        
        if entity is None:
            return {"success": False, "error": error_message}
        
        # Проверяем, что это публичный канал или пользователь
        validation_result = validate_entity_for_download(entity, channel_username)
        
        if not validation_result["valid"]:
            return {"success": False, "error": validation_result["error"]}
        
        # Определяем реальный ID для базы данных и безопасное имя папки
        real_id = entity.username or str(entity.id)
        # Для папки используем префикс, чтобы избежать конфликтов с числовыми ID
        folder_name = entity.username or f"user_{entity.id}" if hasattr(entity, 'first_name') else entity.username or f"channel_{entity.id}"
        
        logging.info(f"Реальный ID для {channel_username}: {real_id}")
        logging.info(f"Имя папки: {folder_name}")
        
        # Очищаем папку канала по имени папки
        clear_downloads(folder_name)
        
        # Сохраняем информацию о канале в базу
        channel_info = get_channel_info(client, entity, output_dir="downloads", folder_name=folder_name)
        logging.info(f"Информация о канале: {channel_info}")
        
        # Добавляем канал в базу данных через API
        api_url = "http://localhost:5000/api/channels"
        response = requests.post(api_url, json=channel_info)
        
        if response.status_code not in [200, 201]:
            logging.error(f"Ошибка добавления канала в БД: {response.text}")
            return {"success": False, "error": f"Ошибка БД: {response.text}"}
        
        # Импортируем сообщения
        include_system_messages = EXPORT_SETTINGS.get("include_system_messages", False)
        include_reposts = EXPORT_SETTINGS.get("include_reposts", True)
        include_polls = EXPORT_SETTINGS.get("include_polls", True)
        message_limit = EXPORT_SETTINGS.get("message_limit", None)

        all_posts = client.iter_messages(
            entity,
            limit=message_limit,
            reverse=True
        )
        
        processed_count = 0
        for post in all_posts:
            try:
                # Обрабатываем сообщение так же, как в main()
                post_data = process_message_for_api(post, real_id, client, folder_name)
                if post_data:
                    # Добавляем пост через API
                    api_url = "http://localhost:5000/api/posts"
                    requests.post(api_url, json=post_data)
                    processed_count += 1
            except Exception as e:
                logging.error(f"Ошибка при обработке сообщения: {str(e)}")
        
        logging.info(f"Обработано сообщений: {processed_count}")
        logging.info(f"Канал {channel_username} импортирован: {processed_count} сообщений")
        return {"success": True, "processed": processed_count}
        
    except Exception as e:
        logging.error(f"Ошибка импорта канала {channel_username}: {str(e)}")
        return {"success": False, "error": str(e)}

def process_message_for_api(post, channel_id, client, folder_name=None):
    """Обрабатывает сообщение для API"""
    try:
        # Получаем папку для канала
        if folder_name:
            channel_folder = get_channel_folder(folder_name)
        else:
            channel_folder = get_channel_folder(channel_id)
        
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
                logging.warning(f"Ошибка при обработке автора репоста: {e}")

        # Обрабатываем реакции
        reactions = None
        if post.reactions and post.reactions.results:
            reactions = {
                "total_count": sum(r.count for r in post.reactions.results),  # Суммируем количество всех реакций
                "recent_reactions": [
                    {"reaction": str(r.reaction), "count": r.count} for r in post.reactions.results
                ]
            }

        grouped_id = getattr(post, "grouped_id", None)
        print(f"process_message_for_api: post.id={getattr(post, 'id', None)} grouped_id={grouped_id}")

        # Обрабатываем информацию о том, является ли это ответом на другое сообщение
        reply_to = None
        if hasattr(post, 'reply_to') and post.reply_to and hasattr(post.reply_to, 'reply_to_msg_id'):
            reply_to = post.reply_to.reply_to_msg_id
            print(f"Сообщение {post.id} является ответом на сообщение {reply_to}")

        return {
            "telegram_id": post.id,
            "channel_id": channel_id,
            "date": post.date.isoformat() if post.date else None,
            "message": post.message or "",
            "media_url": media_path,
            "media_type": media_type,
            "mime_type": mime_type,
            "author_name": sender_name,
            "author_avatar": sender_avatar,
            "author_link": sender_link,
            "repost_author_name": repost_name,
            "repost_author_avatar": repost_avatar,
            "repost_author_link": repost_link,
            "reactions": reactions,
            "grouped_id": grouped_id,
            "reply_to": reply_to
        }
    except Exception as e:
        logging.error(f"Ошибка обработки сообщения {post.id}: {str(e)}")
        return None

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

def save_channel_info(client, channel_username):
    print("== save_channel_info called ==")
    try:
        entity = client.get_entity(channel_username)
        print("== entity получен ==")
        channel_data = get_channel_info(client, entity, output_dir="downloads")
        print("== channel_data:", channel_data)
        channel_data["id"] = entity.username or str(entity.id)
        print("== отправляем в API:", channel_data)
        response = requests.post("http://127.0.0.1:5000/api/channels", json=channel_data)
        print("== ответ API:", response.status_code, response.text)
        if response.status_code == 201:
            print(f"Канал {channel_data['name']} успешно добавлен в базу данных.")
        elif response.status_code == 200:
            print(f"Канал {channel_data['name']} уже существует.")
        else:
            print(f"Ошибка при добавлении канала: {response.text}")
    except Exception as e:
        print(f"Ошибка при сохранении информации о канале: {e}")

def download_channel(channel_name):
    logging.info(f"Начало скачивания канала: {channel_name}")
    # Ваш код для скачивания
    logging.info(f"Канал {channel_name} успешно скачан")

def main(channel_username=None):
    # Очищаем папку текущего канала
    clear_downloads(channel_username)

    start_time = time.time()

    # Подключение к Telegram
    client = connect_to_telegram()
    entity = client.get_entity(channel_username)

    # Сохраняем информацию о канале
    save_channel_info(client, channel_username)

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
        
        # Проверяем, имеет ли пост комментарии
        if post.replies and post.replies.replies > 0:  # Если есть комментарии
            print(f"Пост с ID {post.id} имеет {post.replies.replies} комментариев.")

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