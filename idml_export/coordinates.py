"""
Утилиты для работы с координатами и геометрией IDML
"""

from .constants import mm_to_points


def create_geometric_bounds(y1, x1, y2, x2):
    """
    Создает GeometricBounds в формате InDesign: [y1, x1, y2, x2]
    Все значения в points
    """
    return f"{y1} {x1} {y2} {x2}"


def convert_gallery_layout_to_bounds(layout_json, container_bounds):
    """
    Конвертирует наш gallery layout JSON в IDML GeometricBounds
    
    :param layout_json: dict с полями total_width, total_height, cells
    :param container_bounds: [y1, x1, y2, x2] контейнера в points
    :return: список словарей с bounds для каждой ячейки
    """
    # Распаковываем контейнер
    cont_y1, cont_x1, cont_y2, cont_x2 = container_bounds
    
    # Размеры контейнера
    cont_width = cont_x2 - cont_x1
    cont_height = cont_y2 - cont_y1
    
    # Масштабы из relative units в points
    scale_x = cont_width / layout_json['total_width']
    scale_y = cont_height / layout_json['total_height']
    
    cells_bounds = []
    
    for cell in layout_json['cells']:
        # Конвертируем относительные координаты в абсолютные
        x1 = cont_x1 + cell['x'] * scale_x
        y1 = cont_y1 + cell['y'] * scale_y
        x2 = x1 + cell['width'] * scale_x
        y2 = y1 + cell['height'] * scale_y
        
        cells_bounds.append({
            'image_index': cell['image_index'],
            'bounds': [y1, x1, y2, x2],
            'bounds_string': create_geometric_bounds(y1, x1, y2, x2)
        })
    
    return cells_bounds


def calculate_text_frame_bounds(page_bounds, margins, columns=1, column_gutter=14.17):
    """
    Вычисляет границы текстового фрейма с учетом полей и колонок
    
    :param page_bounds: [y1, x1, y2, x2] страницы
    :param margins: [top, left, bottom, right] в points
    :param columns: количество колонок
    :param column_gutter: расстояние между колонками в points
    :return: dict с границами фрейма и параметрами колонок
    """
    page_y1, page_x1, page_y2, page_x2 = page_bounds
    margin_top, margin_left, margin_bottom, margin_right = margins
    
    # Границы текстовой области (с учетом полей)
    text_y1 = page_y1 + margin_top
    text_x1 = page_x1 + margin_left
    text_y2 = page_y2 - margin_bottom
    text_x2 = page_x2 - margin_right
    
    return {
        'bounds': [text_y1, text_x1, text_y2, text_x2],
        'bounds_string': create_geometric_bounds(text_y1, text_x1, text_y2, text_x2),
        'width': text_x2 - text_x1,
        'height': text_y2 - text_y1,
        'columns': columns,
        'column_gutter': column_gutter
    }


def calculate_image_bounds(text_frame_bounds, aspect_ratio=None, max_height=None):
    """
    Вычисляет границы изображения внутри или над текстовым фреймом
    
    :param text_frame_bounds: dict с bounds текстового фрейма
    :param aspect_ratio: соотношение сторон изображения (width/height)
    :param max_height: максимальная высота в points
    :return: [y1, x1, y2, x2]
    """
    text_y1, text_x1, text_y2, text_x2 = text_frame_bounds['bounds']
    available_width = text_frame_bounds['width']
    
    if aspect_ratio:
        # Вычисляем высоту по соотношению сторон
        height = available_width / aspect_ratio
        
        if max_height and height > max_height:
            height = max_height
            width = height * aspect_ratio
            # Центрируем по горизонтали
            x1 = text_x1 + (available_width - width) / 2
            x2 = x1 + width
        else:
            x1 = text_x1
            x2 = text_x2
    else:
        # Если нет aspect_ratio, используем max_height или дефолт
        height = max_height if max_height else 200
        x1 = text_x1
        x2 = text_x2
    
    y1 = text_y1
    y2 = y1 + height
    
    return [y1, x1, y2, x2]
