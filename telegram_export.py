from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from config import OUTPUT_DIR, EXPORT_SETTINGS
from telegram_client import connect_to_telegram
from message_processing.process_message import process_message
from message_processing.media import process_media
from html_generator import generate_html, generate_index_file, generate_main_page
from utils.time_utils import format_elapsed_time
from weasyprint import HTML
from message_processing.author import download_avatar
from message_processing.channel_info import get_channel_info
import os
import shutil
import time
import argparse
from datetime import datetime
from telethon.tl.types import User, Channel, Chat
import requests

def generate_pdf_from_html_files(output_dir, pdf_filename="posts_feed.pdf"):
    """
    Собирает все HTML-файлы из output_dir и генерирует PDF-ленту.
    
    :param output_dir: Папка, где находятся HTML-файлы.
    :param pdf_filename: Имя выходного PDF-файла.
    """
    # Путь к PDF-файлу
    pdf_path = os.path.join(output_dir, pdf_filename)

    # Список всех HTML-файлов в папке
    html_files = sorted(
        [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".html")]
    )

    if not html_files:
        print("Нет HTML-файлов для генерации PDF.")
        return

    # Собираем содержимое всех HTML-файлов
    combined_html = "<html><head><meta charset='utf-8'><title>Лента постов</title></head><body>"
    for html_file in html_files:
        with open(html_file, "r", encoding="utf-8") as f:
            combined_html += f.read()
    combined_html += "</body></html>"

    # Генерируем PDF с указанием base_url
    print(f"Генерация PDF-файла: {pdf_path}")
    HTML(string=combined_html, base_url=output_dir).write_pdf(pdf_path)
    print(f"PDF-файл успешно создан: {pdf_path}")

def main(download_posts=True, generate_pdf=True, generate_index=True, channel_username=None):
    start_time = time.time()

    if download_posts:
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        client = connect_to_telegram()
        entity = client.get_entity(channel_username)

        # Получаем информацию о канале, пользователе или чате
        channel_info = get_channel_info(client, entity, OUTPUT_DIR)

        # Генерируем заглавную страницу
        generate_main_page(OUTPUT_DIR, channel_info)

        message_limit = EXPORT_SETTINGS.get("message_limit", False)

        all_posts = client.iter_messages(entity, limit=None)
        processed_count = 0
        grouped_messages = {}

        for post in all_posts:
            if not EXPORT_SETTINGS["include_system_messages"] and post.action:
                continue
            if not EXPORT_SETTINGS["include_reposts"] and post.fwd_from:
                continue
            if not EXPORT_SETTINGS["include_polls"] and post.poll:
                continue

            post_data = process_message(post, client)
            post_date = post.date.strftime('%d %B %Y, %H:%M')

            # Сохраняем пост в HTML
            generate_html(post_data, OUTPUT_DIR, post.id, post_date)

            # Сохраняем пост в базу данных через API
            api_data = {
                "telegram_id": str(post.id),
                "title": post_data.get("title", None),
                "content": post_data.get("formatted_text", ""),
                "date": post_date,
                "media": post_data.get("media_html", None),
                "channel_name": channel_info["name"]
            }
            try:
                response = requests.post("http://127.0.0.1:5000/api/posts", json=api_data)
                if response.status_code == 201:
                    print(f"Пост {post.id} успешно добавлен в базу данных.")
                else:
                    print(f"Ошибка при добавлении поста {post.id}: {response.text}")
            except Exception as e:
                print(f"Ошибка при подключении к API: {e}")

            processed_count += 1

            # Прерываем цикл, если достигнут лимит
            if message_limit and processed_count >= message_limit:
                break

        client.disconnect()

        elapsed_time = time.time() - start_time
        time_string = format_elapsed_time(elapsed_time)
        print(f"Экспорт завершён за {time_string}")

    if generate_index:
        # Генерация индексного файла
        generate_index_file(OUTPUT_DIR, channel_username)

    if generate_pdf:
        # Генерация PDF после завершения экспорта
        generate_pdf_from_html_files(OUTPUT_DIR)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Экспорт постов Telegram в HTML и PDF.")
    parser.add_argument(
        "--channel",
        required=True,
        help="Имя Telegram-канала (без @), из которого нужно экспортировать посты."
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Скачивать посты в HTML без генерации PDF."
    )
    parser.add_argument(
        "--only-pdf",
        action="store_true",
        help="Генерировать PDF из уже скачанных HTML-файлов без обновления постов."
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Не генерировать индексный файл со ссылками на посты."
    )
    args = parser.parse_args()

    # Передаём имя канала из аргументов
    channel_username = args.channel

    if args.only_pdf:
        main(download_posts=False, generate_pdf=True, generate_index=not args.no_index, channel_username=channel_username)
    elif args.no_pdf:
        main(download_posts=True, generate_pdf=False, generate_index=not args.no_index, channel_username=channel_username)
    else:
        main(download_posts=True, generate_pdf=True, generate_index=not args.no_index, channel_username=channel_username)