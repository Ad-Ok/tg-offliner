import os

def generate_html(post_data, output_dir, post_id, post_date):
    """Генерирует HTML для одного сообщения."""
    sender_name = post_data["sender_name"]
    sender_avatar = post_data["sender_avatar"]
    sender_link = post_data["sender_link"]
    formatted_text = post_data["formatted_text"]
    media_html = post_data.get("media_html", "")
    reactions_html = post_data.get("reactions_html", "")
    reply_html = post_data.get("reply_html", "")
    repost_html = post_data.get("repost_html", "")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Пост от {post_date}</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: auto; }}
            .media {{ margin: 20px 0; max-width: 100%; }}
            .author {{ display: flex; align-items: center; margin-bottom: 20px; }}
            .author img {{ width: 50px; height: 50px; border-radius: 50%; margin-right: 10px; }}
            .reactions {{ margin-top: 20px; }}
            .reply {{ margin-top: 20px; font-style: italic; color: gray; }}
            .repost {{ margin-top: 20px; font-style: italic; color: blue; }}
        </style>
    </head>
    <body>
        <div class="author">
            <img src="{sender_avatar}" alt="Avatar">
            <a href="{sender_link}" target="_blank">{sender_name}</a>
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
    html_filename = os.path.join(output_dir, f"post_{post_id}_{post_date}.html")
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Сохранён пост: {html_filename}")