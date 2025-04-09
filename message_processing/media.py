import os
from config import OUTPUT_DIR

def process_media(message, client):
    """Обрабатывает медиа."""
    media_html = ""
    media_dir = os.path.join(OUTPUT_DIR, "media")
    os.makedirs(media_dir, exist_ok=True)

    if message.media:
        media_path = client.download_media(
            message,
            file=os.path.join(media_dir, f"media_{message.id}")
        )
        if media_path:
            if media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                media_html = f'<img src="media/{os.path.basename(media_path)}" alt="Media" class="media">'
            elif media_path.lower().endswith(('.mp4', '.webm')):
                media_html = f'<video controls class="media"><source src="media/{os.path.basename(media_path)}" type="video/mp4">Ваш браузер не поддерживает видео.</video>'
            else:
                media_html = f'<a href="media/{os.path.basename(media_path)}" download>Скачать файл</a>'
    return media_html