"""
Утилиты для фильтрации постов в preview и экспорте
Централизованная логика определения видимости постов
"""

def should_hide_media(post):
    """
    Проверяет, должно ли медиа быть скрыто (неподдерживаемые форматы для InDesign)
    
    :param post: объект Post из БД
    :return: True если медиа должно быть скрыто
    """
    if not post.media_url:
        return False
    
    # Неподдерживаемые типы медиа
    unsupported_types = [
        'MessageMediaWebPage',  # Веб-страницы
    ]
    
    # Явно неподдерживаемые типы
    if post.media_type in unsupported_types:
        return True
    
    # MessageMediaDocument только если НЕ изображение
    if post.media_type == 'MessageMediaDocument':
        if not post.mime_type or not post.mime_type.startswith('image/'):
            return True
    
    # webp формат не поддерживается InDesign
    if post.media_url.lower().endswith('.webp'):
        return True
    
    return False


def should_hide_post(post, edits):
    """
    Проверяет, должен ли пост быть скрыт полностью
    
    :param post: объект Post из БД
    :param edits: список Edit объектов для этого поста
    :return: True если пост должен быть скрыт
    """
    # 1. Пост скрыт в базе через edits
    is_hidden_in_db = any(
        e.telegram_id == post.telegram_id and 
        e.channel_id == post.channel_id and
        e.changes.get('hidden') == 'true'
        for e in edits
    )
    
    if is_hidden_in_db:
        return True
    
    # 2. Пост имеет только скрытое медиа и нет текста
    has_hidden_media = should_hide_media(post)
    has_no_text = not post.message or post.message.strip() == ''
    
    if has_hidden_media and has_no_text:
        return True
    
    return False
