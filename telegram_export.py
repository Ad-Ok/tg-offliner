import os
import shutil
from datetime import datetime
from config import CHANNEL_USERNAME, OUTPUT_DIR
from telegram_client import connect_to_telegram
from message_processing.process_message import process_message
from html_generator import generate_html

def main():
    # Очищаем каталог перед загрузкой файлов
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Подключаемся к Telegram
    client = connect_to_telegram()

    # Получаем канал
    channel = client.get_entity(CHANNEL_USERNAME)

    # Скачиваем все сообщения из канала
    all_posts = client.iter_messages(channel, limit=None)

    # Обрабатываем и сохраняем сообщения
    for post in all_posts:
        post_data = process_message(post, client)
        post_date = post.date.strftime('%d %B %Y, %H:%M')
        generate_html(post_data, OUTPUT_DIR, post.id, post_date)

    # Отключаем клиента
    client.disconnect()
    print("Экспорт завершён!")

if __name__ == "__main__":
    main()