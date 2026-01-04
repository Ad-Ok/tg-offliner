"""
Константы и настройки для IDML экспорта
Загружаются из print-config.json (единый источник правды для Python и JS)
"""

import json
import os

# Загружаем конфигурацию из JSON
_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'print-config.json')
with open(_config_path, 'r', encoding='utf-8') as f:
    _config = json.load(f)

# Размеры страниц в миллиметрах (mm) - из конфига
PAGE_SIZES = _config['pageSizes']

# Константы конвертации - из конфига
MM_TO_POINTS = _config['conversion']['mmToPoints']
MM_TO_PX = _config['conversion']['mmToPx']
POINTS_TO_PX = MM_TO_PX / MM_TO_POINTS

# Дефолтные настройки печати - из конфига
DEFAULT_PRINT_SETTINGS = {
    'page_size': _config['defaultPrintSettings']['pageSize'],
    'margins': _config['defaultPrintSettings']['margins'],
    'text_columns': _config['defaultPrintSettings']['textColumns'],
    'column_gutter': _config['defaultPrintSettings']['columnGutter'],
    'master_page_enabled': _config['defaultPrintSettings']['masterPageEnabled'],
    'include_headers_footers': _config['defaultPrintSettings']['includeHeadersFooters'],
}

# Дефолтные настройки для постов - из конфига
DEFAULT_POST_SETTINGS = {
    'text_columns': _config['defaultPostSettings']['textColumns'],
    'image_placement': _config['defaultPostSettings']['imagePlacement'],
    'page_break_before': _config['defaultPostSettings']['pageBreakBefore'],
    'keep_with_next': _config['defaultPostSettings']['keepWithNext'],
}

# Шрифты - из конфига
FONTS = {
    'body': _config['fonts']['body'],
    'body_size': _config['fonts']['bodySize'],
    'heading': _config['fonts']['heading'],
    'heading_size': _config['fonts']['headingSize'],
    'code': _config['fonts']['code'],
    'code_size': _config['fonts']['codeSize'],
    'emoji': _config['fonts']['emoji'],
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
    'PostDate': {
        'font': FONTS['body'],
        'size': 9,
        'color': 'Color/Gray',
        'space_after': 4,
    },
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

# Константы конвертации - из конфига
MM_TO_POINTS = _config['conversion']['mmToPoints']
MM_TO_PX = _config['conversion']['mmToPx']
POINTS_TO_PX = MM_TO_PX / MM_TO_POINTS

# Conversion functions
def mm_to_points(mm):
    """Конвертирует миллиметры в points (1mm = 2.83465 points)"""
    return mm * MM_TO_POINTS

def points_to_mm(points):
    """Конвертирует points в миллиметры"""
    return points / MM_TO_POINTS

def mm_to_px(mm):
    """Конвертирует миллиметры в пиксели при 96 DPI (1mm = 3.7795275591 px)"""
    return mm * MM_TO_PX

def px_to_mm(px):
    """Конвертирует пиксели в миллиметры при 96 DPI"""
    return px / MM_TO_PX

def points_to_px(points):
    """Конвертирует points в пиксели (1 point = 1.333... px)"""
    return points * POINTS_TO_PX

def px_to_points(px):
    """Конвертирует пиксели в points"""
    return px / POINTS_TO_PX
