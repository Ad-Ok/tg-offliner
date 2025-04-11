import os
import shutil
import time
import argparse
from datetime import datetime
from config import CHANNEL_USERNAME, OUTPUT_DIR, EXPORT_SETTINGS
from telegram_client import connect_to_telegram
from message_processing.process_message import process_message
from message_processing.media import process_media
from html_generator import generate_html
from utils.time_utils import format_elapsed_time
from weasyprint import HTML

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

    # Генерируем PDF
    print(f"Генерация PDF-файла: {pdf_path}")
    HTML(string=combined_html).write_pdf(pdf_path)
    print(f"PDF-файл успешно создан: {pdf_path}")

def main(download_posts=True, generate_pdf=True):
    start_time = time.time()

    if download_posts:
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        client = connect_to_telegram()
        channel = client.get_entity(CHANNEL_USERNAME)
        message_limit = EXPORT_SETTINGS.get("message_limit", False)

        all_posts = client.iter_messages(channel, limit=None)
        processed_count = 0
        grouped_messages = {}

        for post in all_posts:
            if not EXPORT_SETTINGS["include_system_messages"] and post.action:
                continue
            if not EXPORT_SETTINGS["include_reposts"] and post.fwd_from:
                continue
            if not EXPORT_SETTINGS["include_polls"] and post.poll:
                continue

            if post.grouped_id:
                # Если сообщение принадлежит группе, добавляем его в группу
                if post.grouped_id not in grouped_messages:
                    grouped_messages[post.grouped_id] = []
                    processed_count += 1  # Увеличиваем счётчик только для новой группы
                grouped_messages[post.grouped_id].append(post)
            else:
                # Обрабатываем одиночное сообщение
                post_data = process_message(post, client)
                post_date = post.date.strftime('%d %B %Y, %H:%M')
                generate_html(post_data, OUTPUT_DIR, post.id, post_date)
                processed_count += 1  # Увеличиваем счётчик для одиночного сообщения

            # Прерываем цикл, если достигнут лимит
            if message_limit and processed_count >= message_limit:
                break

        # Обрабатываем группы сообщений
        for group_id, posts in grouped_messages.items():
            main_post = posts[-1]
            post_data = process_message(main_post, client)
            formatted_text = post_data.get("formatted_text", "")
            media_html = post_data.get("media_html", "")
            for post in posts[:-1]:
                media_html += process_media(post, client)

            post_data["media_html"] = media_html
            post_data["formatted_text"] = formatted_text

            post_date = main_post.date.strftime('%d %B %Y, %H:%M')
            generate_html(post_data, OUTPUT_DIR, main_post.id, post_date)

        client.disconnect()

        elapsed_time = time.time() - start_time
        time_string = format_elapsed_time(elapsed_time)
        print(f"Экспорт завершён за {time_string}")

    if generate_pdf:
        # Генерация PDF после завершения экспорта
        generate_pdf_from_html_files(OUTPUT_DIR)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Экспорт постов Telegram в HTML и PDF.")
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
    args = parser.parse_args()

    if args.only_pdf:
        main(download_posts=False, generate_pdf=True)
    elif args.no_pdf:
        main(download_posts=True, generate_pdf=False)
    else:
        main(download_posts=True, generate_pdf=True)