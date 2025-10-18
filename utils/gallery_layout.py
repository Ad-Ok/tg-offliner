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

        # Финальные корректировки: приводим колонки к общей высоте и подгоняем размеры
        page.adjust()
        page.scale_to_fit(width)

        # Собираем все cells из всех колонок, но гарантируем уникальность photos
        all_cells = []
        used_photos = set()
        for col in page.cols:
            for cell in col.cells:
                if getattr(cell, "is_extension", lambda: False)():
                    continue
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

        _normalize_layout(layout_data)

        print(f"Generated layout with {len(layout_data['cells'])} cells")
        print(f"Gallery layout generated for {len(photos)} images")
        return layout_data

    except Exception as e:
        print(f"Error generating gallery layout: {e}")
        return None


def _normalize_layout(layout_data, precision=6):
    """Snap coordinates to a fixed grid so neighbouring cells touch exactly."""

    cells = layout_data.get('cells', [])
    if not cells:
        return

    precision = max(0, precision)
    scale = 10 ** precision

    def _normalize_axis(start_key: str, size_key: str, total_key: str) -> None:
        total = float(layout_data.get(total_key, 0.0) or 0.0)
        total_int = int(round(total * scale))
        if total_int <= 0:
            return

        edges = set()
        for cell in cells:
            start_int = int(round(cell[start_key] * scale))
            end_int = int(round((cell[start_key] + cell[size_key]) * scale))
            edges.add(start_int)
            edges.add(end_int)

        edges.add(0)
        edges.add(total_int)
        sorted_edges = sorted(edges)

        def snap_int(value: float) -> int:
            raw = int(round(value * scale))
            return min(sorted_edges, key=lambda edge: abs(edge - raw))

        for cell in cells:
            start_int = snap_int(cell[start_key])
            end_int = snap_int(cell[start_key] + cell[size_key])
            if end_int < start_int:
                start_int, end_int = end_int, start_int
            cell[start_key] = round(start_int / scale, precision)
            cell[size_key] = round(max((end_int - start_int) / scale, 0.0), precision)

    _normalize_axis('x', 'width', 'total_width')
    _normalize_axis('y', 'height', 'total_height')

    layout_data['total_width'] = round(int(round((layout_data.get('total_width') or 0.0) * scale)) / scale, precision)
    layout_data['total_height'] = round(int(round((layout_data.get('total_height') or 0.0) * scale)) / scale, precision)

