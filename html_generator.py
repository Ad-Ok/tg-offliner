import os
import shutil  # Для копирования директорий

def copy_static_files(output_dir):
    """Копирует папку static в папку с экспортом."""
    # Путь к папке static относительно корня проекта
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    target_dir = os.path.join(output_dir, "static")

    # Проверяем, существует ли папка static
    if os.path.exists(static_dir):
        # Копируем папку static в папку с экспортом
        shutil.copytree(static_dir, target_dir, dirs_exist_ok=True)
    else:
        print(f"Папка static не найдена по пути: {static_dir}")

def generate_message_html(sender_name, sender_avatar, sender_link, formatted_text, poll_html, media_html, reactions_html, reply_html, repost_html, message_date):
    """Генерирует HTML для одного сообщения."""
    return f"""
    <div class="message">
        <div class="author">
            <img src="{sender_avatar}" alt="Avatar">
            <a href="{sender_link}" target="_blank">{sender_name}</a>
            <span class="date">{message_date}</span>
        </div>
        {repost_html}
        {reply_html}
        <p>{formatted_text}</p>
        {poll_html}
        {media_html}
        {reactions_html}
    </div>
    """

def generate_html(post_data, output_dir, post_id, post_date):
    """Генерирует HTML для одного сообщения."""
    # Копируем статические файлы (если ещё не скопированы)
    copy_static_files(output_dir)

    sender_name = post_data["sender_name"]
    sender_avatar = post_data["sender_avatar"]
    sender_link = post_data["sender_link"]
    formatted_text = post_data["formatted_text"]
    poll_html = post_data.get("poll_html", "")
    media_html = post_data.get("media_html", "")
    reactions_html = post_data.get("reactions_html", "")
    reply_html = post_data.get("reply_html", "")
    repost_html = post_data.get("repost_html", "")
    comments_html = post_data.get("comments_html", "")
    message_date = post_data["message_date"]

    message_html = generate_message_html(
        sender_name, sender_avatar, sender_link, formatted_text, poll_html, media_html, reactions_html, reply_html, repost_html, message_date
    )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Пост от {post_date}</title>
        <link rel="stylesheet" href="static/styles.css">
    </head>
    <body>
        {message_html}
        {comments_html}
    </body>
    </html>
    """

    # Сохраняем HTML
    html_filename = os.path.join(output_dir, f"post_{post_id}_{post_date}.html")
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Сохранён пост: {html_filename}")