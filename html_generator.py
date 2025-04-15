import os
import shutil
from jinja2 import Environment, FileSystemLoader
from utils.date_utils import format_file_date

def copy_static_files(output_dir):
    """Копирует папку static в папку с экспортом."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    target_dir = os.path.join(output_dir, "static")

    if os.path.exists(static_dir):
        shutil.copytree(static_dir, target_dir, dirs_exist_ok=True)
    else:
        print(f"Папка static не найдена по пути: {static_dir}")

def generate_message_html(sender_name, sender_avatar, sender_link, formatted_text, poll_html, media_html, reactions_html, reply_html, repost_html, message_date):
    """Генерирует HTML для одного сообщения или комментария."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("message.html")

    return template.render(
        sender_name=sender_name,
        sender_avatar=sender_avatar,
        sender_link=sender_link,
        formatted_text=formatted_text,
        poll_html=poll_html,
        media_html=media_html,
        reactions_html=reactions_html,
        reply_html=reply_html,
        repost_html=repost_html,
        message_date=message_date,
    )

def generate_html(post_data, output_dir, post_id, post_date):
    """Генерирует HTML для одного сообщения."""
    # Копируем статические файлы (если ещё не скопированы)
    copy_static_files(output_dir)

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("base.html")

    message_html = generate_message_html(
        post_data["sender_name"],
        post_data["sender_avatar"],
        post_data["sender_link"],
        post_data["formatted_text"],
        post_data.get("poll_html", ""),
        post_data.get("media_html", ""),
        post_data.get("reactions_html", ""),
        post_data.get("reply_html", ""),
        post_data.get("repost_html", ""),
        post_data["message_date"],
    )

    html_content = template.render(
        message_html=message_html,
        comments_html=post_data.get("comments_html", ""),
        post_date=post_date,
    )

    # Формируем имя файла с использованием format_file_date
    file_name_date = format_file_date(post_date)
    html_filename = os.path.join(output_dir, f"post_{post_id}_{file_name_date}.html")

    # Сохраняем HTML
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Сохранён пост: {html_filename}")

def generate_index_file(output_dir, channel_username):
    """
    Генерирует индексный HTML-файл со ссылками на все посты и их оригиналы в Telegram.
    
    :param output_dir: Папка, где находятся HTML-файлы постов.
    :param channel_username: Имя канала в Telegram (без @).
    """
    # Список всех HTML-файлов в папке
    html_files = sorted(
        [f for f in os.listdir(output_dir) if f.endswith(".html") and not f.startswith("index")]
    )

    if not html_files:
        print("Нет HTML-файлов для создания индексного файла.")
        return

    # Генерируем ссылки на все файлы
    links = "\n".join(
        [
            f'<li><a href="{file}">{file}</a> - '
            f'<a href="https://t.me/{channel_username}/{file.split("_")[1]}">Оригинал в Telegram</a></li>'
            for file in html_files
        ]
    )

    # Создаём содержимое индексного файла
    index_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Index of Posts</title>
        <link rel="stylesheet" href="static/styles.css">
    </head>
    <body>
        <h1>Index of Posts</h1>
        <ul>
            {links}
        </ul>
    </body>
    </html>
    """

    # Сохраняем индексный файл
    index_file_path = os.path.join(output_dir, "index.html")
    with open(index_file_path, "w", encoding="utf-8") as f:
        f.write(index_content)

    print(f"Индексный файл создан: {index_file_path}")

def generate_main_page(output_dir, channel_info):
    """
    Генерирует заглавную страницу с информацией о канале.
    
    :param output_dir: Папка, где будет сохранён файл.
    :param channel_info: Словарь с информацией о канале (название, таглайн, аватар и т.д.).
    """
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("main_page.html")

    # Рендерим HTML-контент
    html_content = template.render(
        channel_name=channel_info["name"],
        channel_tagline=channel_info["tagline"],
        channel_avatar=channel_info["avatar"],
        channel_username=channel_info["username"],
        channel_creation_date=channel_info["creation_date"],
        channel_subscribers=channel_info["subscribers"]
    )

    # Сохраняем файл
    main_page_path = os.path.join(output_dir, "page_00.html")
    with open(main_page_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Заглавная страница создана: {main_page_path}")