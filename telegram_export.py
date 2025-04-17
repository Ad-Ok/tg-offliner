from telethon.sync import TelegramClient
from config import EXPORT_SETTINGS
from telegram_client import connect_to_telegram
import time
import argparse
import requests
from utils.text_format import parse_entities_to_html
import os

MEDIA_DIR = "media"  # Папка для сохранения медиафайлов
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

    # Получение списка сообщений
    all_posts = client.iter_messages(entity, limit=None)
    processed_count = 0

    for post in all_posts:
        # Преобразуем текст и entities в HTML
        formatted_message = parse_entities_to_html(post.message or "", post.entities or [])

        # Скачиваем медиа, если оно есть
        media_path = None
        media_type = None
        if post.media:
            media_path = client.download_media(post.media, file=os.path.join(MEDIA_DIR, f"{post.id}_media"))
            media_type = type(post.media).__name__  # Тип медиа (например, MessageMediaPhoto)
            print(f"Медиа скачано: {media_path}, тип: {media_type}")

        # Сохраняем ID, дату, текст сообщения, ссылку на медиа и его тип
        api_data = {
            "telegram_id": post.id,
            "date": post.date.strftime('%Y-%m-%dT%H:%M:%S'),  # Преобразуем дату в строку
            "message": formatted_message,  # Сохраняем отформатированный текст
            "media_url": f"http://127.0.0.1:5000/media/{os.path.basename(media_path)}" if media_path else None,
            "media_type": media_type
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