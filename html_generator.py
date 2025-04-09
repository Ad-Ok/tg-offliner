import os

def generate_message_html(sender_name, sender_avatar, sender_link, formatted_text, poll_html, media_html, reactions_html, reply_html, repost_html):
    """Генерирует HTML для одного сообщения."""
    return f"""
    <div class="message">
        <div class="author">
            <img src="{sender_avatar}" alt="Avatar">
            <a href="{sender_link}" target="_blank">{sender_name}</a>
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

    message_html = generate_message_html(
        sender_name, sender_avatar, sender_link, formatted_text, poll_html, media_html, reactions_html, reply_html, repost_html
    )

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
            .comments {{ margin-top: 20px; }}
            .comments ul {{ list-style-type: none; padding: 0; }}
            .comments li {{ margin-bottom: 10px; }}
        </style>
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