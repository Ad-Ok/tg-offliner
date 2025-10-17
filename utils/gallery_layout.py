import json
import os
from photocollage import collage
from PIL import Image

def generate_gallery_layout(image_paths, width=100, border=10):
    """
    Генерирует layout для галереи изображений.

    :param image_paths: Список путей к изображениям
    :param width: Ширина контейнера (пиксели)
    :param border: Отступы между изображениями (пиксели)
    :return: Словарь с данными layout или None при ошибке
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

        # Собираем все cells из всех колонок, но гарантируем уникальность photos
        all_cells = []
        used_photos = set()
        for col in page.cols:
            for cell in col.cells:
                if cell.photo not in used_photos:
                    all_cells.append(cell)
                    used_photos.add(cell.photo)
                    # Ограничиваем количество изображений до исходного количества
                    if len(all_cells) >= len(photos):
                        break
            if len(all_cells) >= len(photos):
                break

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

        print(f"Generated layout with {len(layout_data['cells'])} cells")
        print(f"Gallery layout generated for {len(photos)} images")
        return layout_data

    except Exception as e:
        print(f"Error generating gallery layout: {e}")
        return None