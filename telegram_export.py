import os
import shutil
from config import CHAT_USERNAME, CHANNEL_USERNAME, OUTPUT_DIR
from telegram_client import connect_to_telegram
from message_processor import filter_messages, process_message
from html_generator import generate_html

def main():
    # Очищаем каталог перед загрузкой файлов
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Подключаемся к Telegram
    client = connect_to_telegram()

    # Получаем чат
    chat = client.get_entity(CHAT_USERNAME)

    # Скачиваем все сообщения
    all_posts = client.iter_messages(chat, limit=None)

    # Фильтруем сообщения
    filtered_posts = filter_messages(all_posts, CHANNEL_USERNAME, client)

    # Обрабатываем и сохраняем сообщения
    for post in filtered_posts:
        post_data = process_message(post, client)
        post_date = post.date.strftime('%Y-%m-%d_%H-%М-%S')
        generate_html(post_data, OUTPUT_DIR, post.id, post_date)

    # Отключаем клиента
    client.disconnect()
    print("Экспорт завершён!")

if __name__ == "__main__":
    main()