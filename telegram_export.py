from dotenv import load_dotenv
import os
import shutil
from telethon.sync import TelegramClient
from telethon.utils import html
from datetime import datetime

# Загружаем переменные из .env
load_dotenv()

# Конфигурация
api_id = int(os.getenv("API_ID"))  # Ваш api_id (число)
api_hash = os.getenv("API_HASH")  # Ваш api_hash
phone = os.getenv("PHONE")  # Номер телефона с кодом страны
channel_username = os.getenv("CHANNEL_USERNAME")  # Канал для экспорта
parent_channel_username = os.getenv("PARENT_CHANNEL_USERNAME")  # Родительский канал
output_dir = os.getenv("OUTPUT_DIR", "telegram_export")  # Папка для сохранения

# Очищаем каталог перед загрузкой файлов
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)  # Удаляем каталог и всё его содержимое
os.makedirs(output_dir, exist_ok=True)  # Создаём пустой каталог заново

# Подключаемся к Telegram
client = TelegramClient('session_name', api_id, api_hash)
client.start(phone)

if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input('Введите код из Telegram: '))

# Получаем канал
channel = client.get_entity(channel_username)

# Скачиваем все посты
all_posts = client.iter_messages(channel, limit=None)  # None = все сообщения

# Обрабатываем каждый пост
for post in all_posts:
    # Пропускаем пустые посты (например, удалённые)
    if not post.message and not post.media:
        continue

    # Проверяем, является ли сообщение репостом из указанного "родительского канала"
    if post.fwd_from:
        if post.fwd_from.from_id:  # Если есть ID источника репоста
            source_entity = client.get_entity(post.fwd_from.from_id)
            if hasattr(source_entity, 'username') and source_entity.username != parent_channel_username:
                continue  # Пропускаем сообщения, которые не из указанного канала
        elif post.fwd_from.from_name:  # Если имя источника указано явно
            if post.fwd_from.from_name != parent_channel_username:
                continue  # Пропускаем сообщения, которые не из указанного канала
        else:
            continue  # Пропускаем сообщения без информации об источнике

    # Дату в удобный формат
    post_date = post.date.strftime('%Y-%m-%d_%H-%М-%S')

    # Получаем информацию об авторе
    sender = post.sender  # Для синхронного клиента используем post.sender
    if sender:
        if hasattr(sender, 'first_name'):  # Если это пользователь
            sender_name = sender.first_name
        elif hasattr(sender, 'title'):  # Если это канал
            sender_name = sender.title
        else:
            sender_name = "Неизвестный автор"
    else:
        sender_name = "Неизвестный автор"

    avatar_html = ""

    # Скачиваем аватар автора (если есть)
    if sender and sender.photo:
        avatar_path = client.download_profile_photo(
            sender,
            file=os.path.join(output_dir, f'avatar_{sender.id}.jpg')
        )
        if avatar_path:
            avatar_html = f'<img src="{os.path.basename(avatar_path)}" alt="Avatar" class="avatar">'

    # Используем telethon.utils.html для форматирования текста
    formatted_text = html.unparse(post.message, post.entities) if post.message else ""

    # Обрабатываем репост
    repost_html = ""
    if post.fwd_from:
        if post.fwd_from.from_name:  # Если имя источника указано явно
            source_name = post.fwd_from.from_name
        elif post.fwd_from.from_id:  # Если это канал или пользователь
            source_entity = client.get_entity(post.fwd_from.from_id)
            source_name = source_entity.title if hasattr(source_entity, 'title') else "Неизвестный источник"
        else:
            source_name = "Неизвестный источник"

        repost_html = f'<div class="repost">Репост из: {source_name}</div>'

    # Скачиваем медиа (фото, видео, документы)
    media_html = ""
    if post.media:
        media_path = client.download_media(
            post,
            file=os.path.join(output_dir, f'media_{post.id}_{post_date}')
        )
        if media_path:
            # Определяем тип медиа и добавляем соответствующий HTML
            if media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                media_html = f'<img src="{os.path.basename(media_path)}" alt="Media" class="media">'
            elif media_path.lower().endswith(('.mp4', '.webm')):
                media_html = f'<video controls class="media"><source src="{os.path.basename(media_path)}" type="video/mp4">Ваш браузер не поддерживает видео.</video>'
            else:
                media_html = f'<a href="{os.path.basename(media_path)}" download>Скачать файл</a>'

    # Обрабатываем реакции
    reactions_html = ""
    if post.reactions:
        reactions = post.reactions.results  # Список реакций
        reactions_html = "<div class='reactions'>"
        for reaction in reactions:
            emoji = reaction.reaction  # Эмодзи реакции
            count = reaction.count  # Количество реакций
            reactions_html += f"<span>{emoji} {count}</span> "
        reactions_html += "</div>"

    # Добавляем ссылку на родительское сообщение
    reply_html = ""
    if post.reply_to_msg_id:
        parent_message = client.get_messages(channel, ids=post.reply_to_msg_id)
        if parent_message:
            reply_text = html.unparse(parent_message.message, parent_message.entities) if parent_message.message else "Сообщение без текста"
            reply_html = f'<div class="reply">Цитата: <a href="#post_{parent_message.id}">{reply_text}</a></div>'

    # Сохраняем текст поста в HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Пост от {post_date}</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: auto; }}
            .media {{ margin: 20px 0; max-width: 100%; }}
            .avatar {{ width: 50px; height: 50px; border-radius: 50%; margin-right: 10px; }}
            .author {{ display: flex; align-items: center; margin-bottom: 20px; }}
            .reactions {{ margin-top: 20px; font-size: 16px; }}
            .reactions span {{ margin-right: 10px; }}
            .reply {{ margin-top: 20px; font-style: italic; color: gray; }}
            .repost {{ margin-top: 20px; font-style: italic; color: blue; }}
        </style>
    </head>
    <body>
        <div class="author">
            {avatar_html}
            <span>{sender_name}</span>
        </div>
        <h1>Дата: {post_date}</h1>
        {repost_html}
        {reply_html}
        <p>{formatted_text}</p>
        {media_html}
        {reactions_html}
    </body>
    </html>
    """

    # Сохраняем HTML
    html_filename = f"{output_dir}/post_{post.id}_{post_date}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Сохранён пост: {html_filename}")

# Отключаем клиента
client.disconnect()
print("Экспорт завершён!")