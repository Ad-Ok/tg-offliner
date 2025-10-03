import json
import os
from photocollage import collage
from PIL import Image

def generate_gallery_layout(image_paths, output_json_path, width=1000, border=10):
    """
    Генерирует layout для галереи изображений и сохраняет в JSON.

    :param image_paths: Список путей к изображениям
    :param output_json_path: Путь для сохранения JSON
    :param width: Ширина контейнера (пиксели)
    :param border: Отступы между изображениями (пиксели)
    :return: Путь к JSON файлу или None при ошибке
    """
    if len(image_paths) < 2:
        return None  # Не генерируем layout для одного изображения

    try:
        # Загружаем изображения и создаем Photo объекты
        photos = []
        for path in image_paths:
            if os.path.exists(path):
                img = Image.open(path)
                photo = collage.Photo(path, img.width, img.height)
                photos.append(photo)
            else:
                print(f"Warning: Image not found: {path}")
                return None

        if len(photos) < 2:
            return None

        # Создаем Page (коллажем)
        # target_ratio = 1.0 (квадрат), no_cols = min(3, len(photos))
        no_cols = min(3, len(photos))
        page = collage.Page(width, 1.0, no_cols)

        # Добавляем фото в page
        for photo in photos:
            page.add_cell(photo)

        # Собираем все cells из всех колонок
        all_cells = []
        for col in page.cols:
            all_cells.extend(col.cells)

        # Создаем mapping photo -> index
        photo_to_index = {photo: idx for idx, photo in enumerate(photos)}

        # Генерируем layout data
        layout_data = {
            'total_width': page.w,
            'total_height': page.h,
            'image_count': len(photos),
            'cells': []
        }

        for cell in all_cells:
            photo_index = photo_to_index.get(cell.photo, 0)
            cell_data = {
                'image_index': photo_index,
                'x': cell.x,
                'y': cell.y,
                'width': cell.w,
                'height': cell.h
            }
            layout_data['cells'].append(cell_data)

        # Сохраняем JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)

        print(f"Gallery layout saved to: {output_json_path}")
        return output_json_path

    except Exception as e:
        print(f"Error generating gallery layout: {e}")
        return None

def load_gallery_layout(json_path):
    """
    Загружает layout из JSON файла.

    :param json_path: Путь к JSON файлу
    :return: Словарь с данными layout или None
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading gallery layout: {e}")
        return None