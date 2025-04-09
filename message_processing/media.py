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
            file_extension = media_path.lower().split('.')[-1]
            if file_extension in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
                # Обработка изображений
                media_html = f'<img src="media/{os.path.basename(media_path)}" alt="Media" class="media">'
            elif file_extension in ('mp4', 'webm', 'mkv'):
                # Обработка видео
                media_html = f'''
                <video controls class="media">
                    <source src="media/{os.path.basename(media_path)}" type="video/{file_extension}">
                    Ваш браузер не поддерживает видео.
                </video>
                '''
            elif file_extension in ('mp3', 'wav', 'ogg', 'oga'):
                # Обработка аудио
                if file_extension == 'oga':
                    file_extension = 'ogg'
                media_html = f'''
                <audio controls class="media">
                    <source src="media/{os.path.basename(media_path)}" type="audio/{file_extension}">
                    Ваш браузер не поддерживает аудио.
                </audio>
                '''
            else:
                # Обработка других файлов
                media_html = f'<a href="media/{os.path.basename(media_path)}" download>Скачать файл</a>'
    return media_html