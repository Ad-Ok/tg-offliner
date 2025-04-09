import os
import shutil
import time  # Для замера времени выполнения
from datetime import datetime
from config import CHANNEL_USERNAME, OUTPUT_DIR, EXPORT_SETTINGS
from telegram_client import connect_to_telegram
from message_processing.process_message import process_message
from html_generator import generate_html

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

        # Обрабатываем сообщение
        post_data = process_message(post, client)
        post_date = post.date.strftime('%d %B %Y, %H:%M')
        generate_html(post_data, OUTPUT_DIR, post.id, post_date)

        # Увеличиваем счётчик обработанных сообщений
        processed_count += 1

        # Прерываем цикл, если достигнут лимит
        if message_limit and processed_count >= message_limit:
            break

    # Отключаем клиента
    client.disconnect()

    elapsed_time = time.time() - start_time  # Конец замера времени

    # Преобразуем время в часы, минуты и секунды
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    # Формируем строку времени
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} ч.")
    if minutes > 0 or hours > 0:  # Показываем минуты, если есть часы
        time_parts.append(f"{minutes} мин.")
    time_parts.append(f"{seconds} сек.")

    time_string = " ".join(time_parts)
    print(f"Экспорт завершён за {time_string}")

if __name__ == "__main__":
    main()