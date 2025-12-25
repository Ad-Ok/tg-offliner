"""
Константы и настройки для IDML экспорта
"""

# Размеры страниц в points (1 point = 1/72 inch)
PAGE_SIZES = {
    'A4': {
        'width': 595.28,  # 210mm
        'height': 841.89,  # 297mm
    },
    'US_LETTER': {
        'width': 612.0,  # 8.5 inch
        'height': 792.0,  # 11 inch
    },
}

# Дефолтные настройки печати
DEFAULT_PRINT_SETTINGS = {
    'page_size': 'A4',
    'margins': [56.69, 56.69, 56.69, 56.69],  # top, left, bottom, right (20mm в points)
    'text_columns': 1,
    'column_gutter': 14.17,  # 5mm в points
    'master_page_enabled': True,
    'include_headers_footers': True,
}

# Дефолтные настройки для постов
DEFAULT_POST_SETTINGS = {
    'text_columns': None,  # None = использовать глобальные
    'image_placement': 'above_text',  # 'above_text', 'inline', 'beside_text'
    'page_break_before': False,
    'keep_with_next': False,
}

# Шрифты
FONTS = {
    'body': 'Arial',
    'body_size': 10,
    'heading': 'Arial',
    'heading_size': 14,
    'code': 'Courier New',
    'code_size': 9,
    'emoji': 'Segoe UI Emoji',  # Fallback: Apple Color Emoji, Noto Color Emoji
}

# Telegram Entity types → Character Style mapping
ENTITY_TO_CHAR_STYLE = {
    'MessageEntityBold': 'TelegramBold',
    'MessageEntityItalic': 'TelegramItalic',
    'MessageEntityCode': 'TelegramCode',
    'MessageEntityPre': 'TelegramCodeBlock',
    'MessageEntityTextUrl': 'TelegramLink',
    'MessageEntityUrl': 'TelegramLink',
    'MessageEntityMention': 'TelegramMention',
    'MessageEntityStrike': 'TelegramStrike',
    'MessageEntityUnderline': 'TelegramUnderline',
}

# Paragraph Styles
PARAGRAPH_STYLES = {
    'PostHeader': {
        'font': FONTS['body'],
        'size': 9,
        'color': 'Color/Gray',
        'space_after': 6,
    },
    'PostBody': {
        'font': FONTS['body'],
        'size': FONTS['body_size'],
        'color': 'Color/Black',
        'space_after': 12,
    },
    'PostQuote': {
        'font': FONTS['body'],
        'size': FONTS['body_size'],
        'color': 'Color/DarkGray',
        'left_indent': 14.17,  # 5mm
        'space_after': 12,
    },
    'PostFooter': {
        'font': FONTS['body'],
        'size': 8,
        'color': 'Color/Gray',
        'space_after': 20,
    },
}

# Conversion: mm to points
def mm_to_points(mm):
    """Конвертирует миллиметры в points (1mm = 2.83465 points)"""
    return mm * 2.83465

# Conversion: points to mm
def points_to_mm(points):
    """Конвертирует points в миллиметры"""
    return points / 2.83465
