import json
import os
from photocollage import collage
from PIL import Image

def generate_gallery_layout(image_paths, width=100, border=10, columns=None, no_crop=False):
    """
    Генерирует layout для галереи изображений.

    :param image_paths: Список путей к изображениям
    :param width: Ширина контейнера (пиксели)
    :param border: Отступы между изображениями (пиксели)
    :param columns: Количество колонок (1-4) или None для авто-режима
    :param no_crop: Если True, не кропить изображения и использовать masonry-style layout
    :return: Словарь с данными layout или None при ошибке
    """
    if len(image_paths) < 2:
        return None  # Не генерируем layout для одного изображения

    try:
        # Загружаем изображения
        images_info = []
        for path in image_paths:
            if os.path.exists(path):
                with Image.open(path) as img:
                    images_info.append({
                        'path': path,
                        'width': img.width,
                        'height': img.height
                    })
            else:
                print(f"Warning: Image not found: {path}")
                return None

        if len(images_info) < 2:
            return None

        # Если выбрана 1 колонка - просто выстраиваем картинки одна под другой без кадрирования
        if columns == 1:
            layout_data = {
                'total_width': width,
                'total_height': 0,
                'image_count': len(images_info),
                'cells': []
            }
            
            current_y = 0
            for idx, img_info in enumerate(images_info):
                # Масштабируем изображение по ширине, сохраняя пропорции
                scale = width / img_info['width']
                scaled_height = img_info['height'] * scale
                
                cell_data = {
                    'image_index': idx,
                    'x': 0,
                    'y': current_y,
                    'width': width,
                    'height': scaled_height
                }
                layout_data['cells'].append(cell_data)
                current_y += scaled_height
            
            layout_data['total_height'] = current_y
            print(f"Generated single-column layout for {len(images_info)} images without cropping")
            return layout_data

        # Для остальных случаев используем photocollage
        photos = []
        for img_info in images_info:
            photo = collage.Photo(img_info['path'], img_info['width'], img_info['height'])
            photos.append(photo)

        # Создаем Page (коллажем)
        # Используем свободное соотношение сторон (вместо квадрата 1.0)
        # Вычисляем среднее соотношение сторон всех фото
        avg_ratio = sum(photo.w / photo.h for photo in photos) / len(photos)
        # Ограничиваем от 0.5 (вертикальный) до 3.0 (очень горизонтальный)
        target_ratio = max(0.5, min(3.0, avg_ratio))
        
        # no_cols определяется параметром columns или авто
        if columns is not None and 2 <= columns <= 4:
            no_cols = min(columns, len(photos))
        else:
            no_cols = min(3, len(photos))

        # Try photocollage, but fall back to our own algorithm if it fails
        layout_data = None
        try:
            page = collage.Page(width, target_ratio, no_cols)

            # Добавляем фото в page
            for photo in photos:
                page.add_cell(photo)

            # Финальные корректировки: приводим колонки к общей высоте и подгоняем размеры
            # В режиме no_crop пропускаем adjust и scale_to_fit, чтобы избежать кропирования
            if not no_crop:
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

            # Validate: check for broken cells (zero dimensions) or missing images
            has_broken_cells = any(
                c['width'] <= 0 or c['height'] <= 0
                for c in layout_data['cells']
            )
            missing_images = len(layout_data['cells']) < len(photos)

            if has_broken_cells or missing_images:
                print(f"photocollage produced invalid layout (broken_cells={has_broken_cells}, missing={missing_images}), using fallback")
                layout_data = None

        except Exception as pc_err:
            print(f"photocollage failed: {pc_err}, using fallback")
            layout_data = None

        # Fallback: simple grid layout based on actual image proportions
        if layout_data is None:
            layout_data = _generate_fallback_layout(images_info, width, no_cols)

        _normalize_layout(layout_data)

        # Clamp total_height to max 150% of total_width to avoid overly tall layouts
        max_height = width * 1.5
        if layout_data['total_height'] > max_height:
            scale = max_height / layout_data['total_height']
            layout_data['total_height'] = max_height
            for cell in layout_data['cells']:
                cell['y'] *= scale
                cell['height'] *= scale
            _normalize_layout(layout_data)

        print(f"Generated layout with {len(layout_data['cells'])} cells")
        print(f"Gallery layout generated for {len(photos)} images")
        return layout_data

    except Exception as e:
        print(f"Error generating gallery layout: {e}")
        return None


def _generate_fallback_layout(images_info, width, no_cols):
    """
    Simple fallback layout when photocollage fails or produces broken results.
    
    Strategy for 2 images: side by side, heights equalized.
    Strategy for 3+ images: first image takes left portion, rest stack on the right.
    All cells use object-fit:cover so exact proportions are less critical.
    """
    n = len(images_info)
    
    if n == 2:
        # Side by side, each takes 50% width, heights proportional then equalized
        r0 = images_info[0]['height'] / images_info[0]['width']
        r1 = images_info[1]['height'] / images_info[1]['width']
        col_w = width / 2
        h0 = col_w * r0
        h1 = col_w * r1
        row_h = (h0 + h1) / 2  # average height
        # Clamp to reasonable range
        row_h = max(col_w * 0.4, min(col_w * 2.0, row_h))
        
        return {
            'total_width': width,
            'total_height': row_h,
            'image_count': n,
            'cells': [
                {'image_index': 0, 'x': 0, 'y': 0, 'width': col_w, 'height': row_h},
                {'image_index': 1, 'x': col_w, 'y': 0, 'width': col_w, 'height': row_h},
            ]
        }
    
    # 3+ images: first image on the left (2/3 width), rest stacked on the right (1/3 width)
    left_w = width * 2 / 3
    right_w = width - left_w
    right_count = n - 1
    
    # Calculate total height based on the first image's proportions
    r0 = images_info[0]['height'] / images_info[0]['width']
    left_h = left_w * r0
    # Clamp left height to reasonable range
    left_h = max(width * 0.3, min(width * 1.4, left_h))
    
    total_h = left_h
    right_cell_h = total_h / right_count
    
    cells = [
        {'image_index': 0, 'x': 0, 'y': 0, 'width': left_w, 'height': total_h}
    ]
    
    for i in range(right_count):
        cells.append({
            'image_index': i + 1,
            'x': left_w,
            'y': i * right_cell_h,
            'width': right_w,
            'height': right_cell_h
        })
    
    return {
        'total_width': width,
        'total_height': total_h,
        'image_count': n,
        'cells': cells
    }


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

