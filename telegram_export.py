import os
import shutil
import time  # Для замера времени выполнения
from datetime import datetime
from config import CHANNEL_USERNAME, OUTPUT_DIR, EXPORT_SETTINGS
from telegram_client import connect_to_telegram
from message_processing.process_message import process_message
from message_processing.media import process_media  # Импортируем process_media
from html_generator import generate_html
from utils.time_utils import format_elapsed_time

def main():
    start_time = time.time()  # Начало замера времени

    # Очищаем каталог перед загрузкой файлов
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Подключаемся к Telegram
    client = connect_to_telegram()

    # Получаем канал
    channel = client.get_entity(CHANNEL_USERNAME)

    # Получаем лимит сообщений из настроек
    message_limit = EXPORT_SETTINGS.get("message_limit", False)

    # Скачиваем сообщения
    all_posts = client.iter_messages(channel, limit=None)

    # Счётчик обработанных сообщений
    processed_count = 0

    # Словарь для хранения групп сообщений
    grouped_messages = {}

    # Обрабатываем и сохраняем сообщения
    for post in all_posts:
        # Пропускаем системные сообщения, если они отключены
        if not EXPORT_SETTINGS["include_system_messages"] and post.action:
            continue

        # Пропускаем репосты, если они отключены
        if not EXPORT_SETTINGS["include_reposts"] and post.fwd_from:
            continue

        # Пропускаем голосования, если они отключены
        if not EXPORT_SETTINGS["include_polls"] and post.poll:
            continue

        # Проверяем, является ли сообщение частью группы
        if post.grouped_id:
            if post.grouped_id not in grouped_messages:
                grouped_messages[post.grouped_id] = []
            grouped_messages[post.grouped_id].append(post)
        else:
            # Обрабатываем одиночное сообщение
            post_data = process_message(post, client)
            post_date = post.date.strftime('%d %B %Y, %H:%M')
            generate_html(post_data, OUTPUT_DIR, post.id, post_date)

        # Увеличиваем счётчик обработанных сообщений
        processed_count += 1

        # Прерываем цикл, если достигнут лимит
        if message_limit and processed_count >= message_limit:
            break

    # Обрабатываем группы сообщений
    for group_id, posts in grouped_messages.items():
        # Обрабатываем последнюю часть группы как основное сообщение
        main_post = posts[-1]  # Последнее сообщение в группе
        post_data = process_message(main_post, client)

        # Сохраняем текст из main_post
        formatted_text = post_data.get("formatted_text", "")

        # Инициализируем media_html перед добавлением медиа
        media_html = post_data.get("media_html", "")  # Сохраняем медиа из main_post, если есть
        for post in posts[:-1]:  # Пропускаем main_post, так как он уже обработан
            media_html += process_media(post, client)

        # Обновляем media_html и текст в данных сообщения
        post_data["media_html"] = media_html
        post_data["formatted_text"] = formatted_text  # Убедимся, что текст main_post не теряется

        # Генерируем HTML для группы
        post_date = main_post.date.strftime('%d %B %Y, %H:%M')
        generate_html(post_data, OUTPUT_DIR, main_post.id, post_date)

    # Отключаем клиента
    client.disconnect()

    elapsed_time = time.time() - start_time  # Конец замера времени

    # Преобразуем время в строку
    time_string = format_elapsed_time(elapsed_time)
    print(f"Экспорт завершён за {time_string}")

if __name__ == "__main__":
    main()