"""
Основной класс для создания IDML документов
"""

import os
import zipfile
import uuid
import shutil
from lxml import etree as ET
from datetime import datetime
from PIL import Image

from .constants import PAGE_SIZES, DEFAULT_PRINT_SETTINGS, DEFAULT_POST_SETTINGS, mm_to_points, FONTS
from .styles import generate_styles_xml
from .coordinates import calculate_text_frame_bounds
from .resources import generate_fonts_xml, generate_graphic_xml, generate_preferences_xml


class IDMLBuilder:
    """
    Билдер для создания IDML документов из Telegram постов
    """
    
    def __init__(self, channel, print_settings=None):
        """
        :param channel: объект Channel из БД
        :param print_settings: dict с глобальными настройками печати (margins в мм)
        """
        self.channel = channel
        self.settings = {**DEFAULT_PRINT_SETTINGS, **(print_settings or {})}
        
        # Конвертируем margins и column_gutter из мм в пункты используя функцию
        self.settings['margins'] = [mm_to_points(m) for m in self.settings['margins']]
        if 'column_gutter' in self.settings:
            self.settings['column_gutter'] = mm_to_points(self.settings['column_gutter'])
        
        # Генераторы ID
        self._id_counter = 100
        
        # Размеры страницы (инициализируем из настроек)
        page_size_mm = PAGE_SIZES[self.settings['page_size']]
        self.page_width = mm_to_points(page_size_mm['width'])
        self.page_height = mm_to_points(page_size_mm['height'])
        
        # Структура документа
        self.spreads = []
        self.stories = []
        self.master_spreads = []
        self.links = []  # Ссылки на изображения
        self.media_files = []  # Список медиа-файлов для упаковки [{source, dest}]
        
        # Текущая позиция для размещения контента
        self.current_page = None
        self.current_y = 0
        
    def next_id(self, prefix='u'):
        """Генерирует уникальный ID для IDML элементов"""
        self._id_counter += 1
        return f"{prefix}{self._id_counter}"
    
    def create_document(self):
        """Создает пустой документ без страниц (для frozen layout)"""
        # Размер страницы из констант (в мм), конвертируем в points
        page_size_mm = PAGE_SIZES[self.settings['page_size']]
        width = mm_to_points(page_size_mm['width'])
        height = mm_to_points(page_size_mm['height'])
        
        # Сохраняем размеры для использования в add_page
        self.page_width = width
        self.page_height = height
        
        # НЕ создаем spreads здесь - они будут созданы в add_page/add_frozen_post
        
        return None
    
    def get_all_pages(self):
        """Возвращает список всех страниц из всех spreads"""
        all_pages = []
        for spread in self.spreads:
            all_pages.extend(spread['pages'])
        return all_pages
    
    def add_page(self, is_right_page=None):
        """
        Добавляет новую страницу в документ с правильной структурой разворотов по модели InDesign
        
        :param is_right_page: True для правой страницы, False для левой, None - авто
        :return: новая страница
        """
        page_id = self.next_id('page_')
        
        all_pages = self.get_all_pages()
        page_count = len(all_pages)
        page_number = page_count + 1
        
        # InDesign ItemTransform для страницы
        # Для правых страниц: 1 0 0 1 0 -pageHeight/2
        # Для левых страниц: 1 0 0 1 -pageWidth -pageHeight/2
        center_offset = -self.page_height / 2
        
        if page_count == 0:
            # Страница 1 - одиночная правая (титул)
            new_page = {
                'id': page_id,
                'bounds': [0, 0, self.page_height, self.page_width],
                'frames': [],
                'item_transform': f'1 0 0 1 0 {center_offset}',
                'name': str(page_number)
            }
            
            spread_id = self.next_id('spread_')
            spread = {
                'id': spread_id,
                'pages': [new_page],
                'page_count': 1,
                'binding_location': 0,  # Одиночная правая
                'item_transform': '1 0 0 1 0 0'
            }
            self.spreads.append(spread)
            
        elif page_count % 2 == 1:
            # Четные страницы (2, 4, 6...) - начинаем новый разворот с ЛЕВОЙ страницы
            new_page = {
                'id': page_id,
                'bounds': [0, 0, self.page_height, self.page_width],
                'frames': [],
                'item_transform': f'1 0 0 1 {-self.page_width} {center_offset}',  # Левая страница сдвинута влево
                'name': str(page_number)
            }
            
            spread_id = self.next_id('spread_')
            # Каждый следующий spread сдвигается вниз на page_height относительно предыдущего
            # spread_index (0-based): 0 = cover (Y=0), 1 = pages 2-3, 2 = pages 4-5, ...
            spread_index = len(self.spreads)
            spread_y = spread_index * self.page_height
            spread = {
                'id': spread_id,
                'pages': [new_page],
                'page_count': 1,  # Пока одна страница, будет 2 после добавления правой
                'binding_location': 1,  # Разворот
                'item_transform': f'1 0 0 1 0 {spread_y}'
            }
            self.spreads.append(spread)
            
        else:
            # Нечетные страницы (3, 5, 7...) - добавляем ПРАВУЮ страницу в текущий разворот
            new_page = {
                'id': page_id,
                'bounds': [0, 0, self.page_height, self.page_width],
                'frames': [],
                'item_transform': f'1 0 0 1 0 {center_offset}',  # Правая страница
                'name': str(page_number)
            }
            
            # Добавляем в текущий spread
            self.spreads[-1]['pages'].append(new_page)
            self.spreads[-1]['page_count'] = 2  # Теперь разворот полный
        
        return new_page
    
    def add_text_story(self, content, style='PostBody'):
        """
        Добавляет текстовую Story
        
        :param content: текст (пока простой, без форматирования)
        :param style: имя ParagraphStyle
        :return: story_id
        """
        story_id = self.next_id('story_')
        
        story = {
            'id': story_id,
            'content': content,
            'style': style
        }
        
        self.stories.append(story)
        return story_id
    
    def add_text_frame(self, story_id, bounds, page_index=None, vertical_justification='TopAlign'):
        """
        Добавляет текстовый фрейм на страницу
        
        :param story_id: ID Story
        :param bounds: [y1, x1, y2, x2]
        :param page_index: индекс страницы (0-based), если None - текущая страница
        :param vertical_justification: вертикальное выравнивание ('TopAlign', 'CenterAlign', 'BottomAlign')
        """
        frame_id = self.next_id('frame_')
        
        frame = {
            'id': frame_id,
            'type': 'TextFrame',
            'story_id': story_id,
            'bounds': bounds,
            'vertical_justification': vertical_justification
        }
        
        # Добавляем на указанную или текущую страницу
        if page_index is not None:
            all_pages = self.get_all_pages()
            target_page = all_pages[page_index]
        else:
            target_page = self.current_page
            
        target_page['frames'].append(frame)
        return frame_id
    
    def get_image_dimensions(self, image_path):
        """
        Получает размеры изображения в пикселях
        
        :param image_path: путь к изображению
        :return: (width, height) или None если не удалось прочитать
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            print(f"Не удалось получить размеры изображения {image_path}: {e}")
            return None
    
    def calculate_image_bounds(self, image_path, max_width, start_y, max_height=None):
        """
        Вычисляет bounds для изображения с сохранением пропорций
        
        :param image_path: путь к изображению
        :param max_width: максимальная ширина в points
        :param start_y: начальная Y координата
        :param max_height: максимальная высота в points (опционально)
        :return: [y1, x1, y2, x2] или None
        """
        dimensions = self.get_image_dimensions(image_path)
        if not dimensions:
            return None
        
        img_width, img_height = dimensions
        aspect_ratio = img_width / img_height
        
        # Вычисляем размеры с сохранением пропорций
        width = max_width
        height = width / aspect_ratio
        
        # Ограничиваем высоту если нужно
        if max_height and height > max_height:
            height = max_height
            width = height * aspect_ratio
        
        # Центрируем по горизонтали
        from .coordinates import calculate_text_frame_bounds
        page_bounds = self.current_page['bounds']
        text_area = calculate_text_frame_bounds(
            page_bounds,
            self.settings['margins']
        )
        
        x1 = text_area['bounds'][1]
        x2 = x1 + width
        y1 = start_y
        y2 = start_y + height
        
        return [y1, x1, y2, x2]
    
    def add_image_frame(self, image_path, bounds, page_index=None, stroke_weight=0, corner_radius=0):
        """
        Добавляет фрейм с изображением
        
        :param image_path: абсолютный путь к изображению
        :param bounds: [y1, x1, y2, x2]
        :param page_index: индекс страницы (0-based), если None - текущая страница
        :param stroke_weight: толщина рамки в points (0 = без рамки)
        :param corner_radius: радиус скругления углов в points (0 = без скругления)
        """
        frame_id = self.next_id('frame_')
        link_id = self.next_id('link_')
        
        # Используем абсолютный путь к файлу
        absolute_path = os.path.abspath(image_path)
        
        frame = {
            'id': frame_id,
            'type': 'Rectangle',
            'bounds': bounds,
            'stroke_weight': stroke_weight,  # Толщина рамки в points
            'corner_radius': corner_radius,  # Радиус скругления углов в points
            'image': {
                'link_id': link_id,
                'path': absolute_path  # Абсолютный путь к файлу
            }
        }
        
        # Добавляем на указанную или текущую страницу
        if page_index is not None:
            all_pages = self.get_all_pages()
            target_page = all_pages[page_index]
        else:
            target_page = self.current_page
            
        target_page['frames'].append(frame)
        
        # Добавляем ссылку в список
        self.links.append({
            'id': link_id,
            'path': absolute_path
        })
        
        return frame_id
    
    def add_post(self, post, downloads_dir):
        """
        Добавляет пост с текстом и медиа
        
        :param post: объект Post из БД
        :param downloads_dir: путь к директории с загруженными файлами
        :return: высота добавленного контента
        """
        from .coordinates import calculate_text_frame_bounds
        
        page_bounds = self.current_page['bounds']
        text_area = calculate_text_frame_bounds(
            page_bounds,
            self.settings['margins']
        )
        
        start_y = self.current_y
        content_height = 0
        
        # Получаем настройки размещения изображения
        post_settings = post.print_settings or {}
        image_placement = post_settings.get('image_placement', DEFAULT_POST_SETTINGS['image_placement'])
        
        # Сначала добавляем текст если есть
        if post.message:
            story_id = self.add_text_story(post.message, 'PostBody')
            
            # Уменьшенный фрейм высотой 75pt (было 150pt)
            text_height = 75
            frame_bounds = [
                self.current_y,
                text_area['bounds'][1],
                self.current_y + text_height,
                text_area['bounds'][3]
            ]
            
            self.add_text_frame(story_id, frame_bounds)
            self.current_y += text_height + 10
            content_height += text_height + 10
        
        # Потом добавляем медиа под текстом
        if post.media_url:
            media_full_path = os.path.join(downloads_dir, post.media_url)
            
            if os.path.exists(media_full_path):
                # Вычисляем bounds для изображения
                available_width = text_area['width']
                max_height = 400  # максимальная высота изображения в points (~14cm)
                
                image_bounds = self.calculate_image_bounds(
                    media_full_path,
                    available_width,
                    self.current_y,
                    max_height
                )
                
                if image_bounds:
                    self.add_image_frame(media_full_path, image_bounds)
                    image_height = image_bounds[2] - image_bounds[0]
                    self.current_y += image_height + 10  # отступ после изображения
                    content_height += image_height + 10
        
        # Отступ между постами
        self.current_y += 20
        content_height += 20
        
        return content_height
    
    def add_frozen_post(self, post_data, page_number):
        """
        Добавляет пост из frozen layout с точными координатами
        
        :param post_data: словарь с данными поста из frozen layout
        :param page_number: номер страницы (1-based)
        """
        from .constants import mm_to_points
        
        # Убеждаемся что нужное количество страниц существует
        all_pages = self.get_all_pages()
        while len(all_pages) < page_number:
            self.add_page()
            all_pages = self.get_all_pages()
        
        # Получаем bounds из frozen данных (в миллиметрах)
        bounds_mm = post_data.get('bounds', {})
        
        # Frozen координаты:
        # - top: относительно page-break маркера (ПОСЛЕ top margin) - нужно добавить margin
        # - left: относительно containerRect.left (УЖЕ включает left margin) - НЕ добавлять margin
        top_margin_pt = self.settings['margins'][0]  # top margin
        
        # Конвертируем bounds в points для InDesign
        top_pt = mm_to_points(bounds_mm['top']) + top_margin_pt  # Добавляем top margin
        left_pt = mm_to_points(bounds_mm['left'])  # НЕ добавляем left margin (уже учтен)
        width_pt = mm_to_points(bounds_mm['width'])
        height_pt = mm_to_points(bounds_mm['height'])
        
        # InDesign bounds: [y1, x1, y2, x2]
        frame_bounds = [
            top_pt,                  # y1 (top)
            left_pt,                 # x1 (left)
            top_pt + height_pt,      # y2 (bottom)
            left_pt + width_pt       # x2 (right)
        ]
        
        # Получаем telegram_id и channel_id для запроса из БД
        telegram_id = post_data.get('telegram_id')
        channel_id = post_data.get('channel_id')
        
        # Загружаем пост из базы данных
        from models import Post
        post = Post.query.filter_by(
            telegram_id=telegram_id,
            channel_id=channel_id
        ).first()
        
        if not post:
            return
        
        # Проверяем условия для показа автора (аватар + имя)
        # Показываем только для комментариев от сторонних авторов (не канал/discussion group)
        should_show_author = False
        if post.reply_to:  # Это комментарий
            author_link = post.author_link
            if author_link:
                # Проверяем что автор НЕ является каналом или discussion group
                is_owner = False
                
                # Проверяем совпадение с каналом по username
                if channel_id and author_link == f"https://t.me/{channel_id}":
                    is_owner = True
                
                # Проверяем совпадение с каналом по числовому ID (с префиксом channel_)
                if not is_owner and channel_id and channel_id.startswith('channel_'):
                    numeric_id = channel_id.replace('channel_', '')
                    if author_link == f"https://t.me/c/{numeric_id}":
                        is_owner = True
                
                # Проверяем совпадение с каналом по чистому числовому ID
                if not is_owner and channel_id and channel_id.isdigit() and author_link == f"https://t.me/c/{channel_id}":
                    is_owner = True
                
                # Проверяем совпадение с discussion group
                if not is_owner and self.channel.discussion_group_id:
                    if author_link == f"https://t.me/c/{self.channel.discussion_group_id}":
                        is_owner = True
                
                should_show_author = not is_owner
        
        # Вычисляем размеры и позицию для элементов автора
        # Аватар: 32x32px = ~11.3x11.3mm = ~32x32pt
        # Отступ между элементами: 5mm = ~14.17pt
        if should_show_author and post.author_name:
            from .constants import mm_to_points
            
            avatar_size_pt = 32  # 32pt = ~11.3mm
            author_spacing_pt = mm_to_points(5)  # 5mm между аватаром и именем
            author_block_height_pt = avatar_size_pt + mm_to_points(2)  # +2mm отступ снизу
            
            # Аватар: слева от текста, в начале поста
            avatar_bounds = [
                top_pt,  # y1
                left_pt,  # x1
                top_pt + avatar_size_pt,  # y2
                left_pt + avatar_size_pt  # x2
            ]
            
            # Имя автора: справа от аватара
            author_name_left_pt = left_pt + avatar_size_pt + author_spacing_pt
            author_name_width_pt = width_pt - avatar_size_pt - author_spacing_pt
            author_name_bounds = [
                top_pt,  # y1
                author_name_left_pt,  # x1
                top_pt + avatar_size_pt,  # y2 (той же высоты что аватар)
                author_name_left_pt + author_name_width_pt  # x2
            ]
            
            # Добавляем аватар если есть
            if post.author_avatar:
                avatar_path = os.path.join('/app/downloads', post.author_avatar)
                if os.path.exists(avatar_path):
                    print(f"✅ Adding author avatar: {avatar_path}")
                    self.add_image_frame(
                        avatar_path,
                        avatar_bounds,
                        page_index=page_number - 1,
                        stroke_weight=0,
                        corner_radius=16  # Полное скругление (половина от 32pt)
                    )
                else:
                    print(f"⚠️ Author avatar not found: {avatar_path}")
            
            # Добавляем имя автора с вертикальным центрированием
            author_story_id = self.add_text_story(f'<p style="Author">{post.author_name}</p>', 'Author')
            self.add_text_frame(author_story_id, author_name_bounds, page_index=page_number - 1, vertical_justification='CenterAlign')
            print(f"✅ Added author name: {post.author_name}")
            
            # Сдвигаем верхнюю границу текста вниз, чтобы он начинался после автора
            frame_bounds[0] += author_block_height_pt  # top
            # И уменьшаем высоту на ту же величину
            height_pt -= author_block_height_pt
            frame_bounds[2] = frame_bounds[0] + height_pt  # bottom (пересчитываем)
        
        # Добавляем текст с датой если есть
        if post.message:
            # Формируем текст с датой в начале (если дата есть)
            full_text = post.message
            if post_data.get('date'):
                # Вставляем дату в начало того же блока с переводом строки
                date_paragraph = f'<p style="PostDate">{post_data["date"]}</p>\n'
                full_text = date_paragraph + post.message
                print(f"✅ Added date: {post_data['date']}")
            
            # Используем исходный текст из базы (с HTML форматированием) + дата
            story_id = self.add_text_story(full_text, 'PostBody')
            self.add_text_frame(story_id, frame_bounds, page_index=page_number - 1)
        
        # Добавляем медиа элементы
        from utils.post_filtering import should_hide_media
        
        media_elements = post_data.get('media', [])
        for media_elem in media_elements:
            if media_elem['type'] == 'image':
                # Проверяем валидность bounds перед обработкой
                media_bounds_mm = media_elem.get('bounds', {})
                media_w = media_bounds_mm.get('width', 0)
                media_h = media_bounds_mm.get('height', 0)
                media_t = media_bounds_mm.get('top', 0)
                media_l = media_bounds_mm.get('left', 0)
                
                if media_w <= 0 or media_h <= 0 or media_t < -10 or media_l < -10:
                    print(f"⏭️ Skipping media with invalid bounds: top={media_t}, left={media_l}, w={media_w}, h={media_h}")
                    continue
                
                # Для галерей: media_elem['telegram_id'] содержит ID отдельной картинки
                # Для одиночных изображений: используем telegram_id поста
                media_telegram_id = media_elem.get('telegram_id', telegram_id)
                
                # Загружаем пост с этим медиа из базы
                media_post = Post.query.filter_by(
                    telegram_id=media_telegram_id,
                    channel_id=channel_id
                ).first()
                
                if not media_post or not media_post.media_url:
                    print(f"⚠️ Media post not found: {media_telegram_id}")
                    continue
                
                # Применяем фильтр медиа
                if should_hide_media(media_post):
                    print(f"⏭️ Skipping unsupported media type: {media_post.media_type} ({media_post.media_url})")
                    continue
                
                # Получаем border_width из frozen данных (для галерей)
                # border_width приходит как строка с пикселями ('2', '4', etc.)
                from .constants import px_to_points
                border_width_px = float(media_elem.get('border_width', 0))
                border_width_pt = px_to_points(border_width_px) if border_width_px > 0 else 0
                
                # Координаты медиа в миллиметрах
                media_bounds_mm = media_elem['bounds']
                
                # Конвертируем в points (с учетом margins)
                media_top_pt = mm_to_points(media_bounds_mm['top']) + top_margin_pt
                media_left_pt = mm_to_points(media_bounds_mm['left'])
                media_width_pt = mm_to_points(media_bounds_mm['width'])
                media_height_pt = mm_to_points(media_bounds_mm['height'])
                
                media_frame_bounds = [
                    media_top_pt,
                    media_left_pt,
                    media_top_pt + media_height_pt,
                    media_left_pt + media_width_pt
                ]
                
                # Путь к изображению из базы (channel_id/media/file.jpg)
                image_path = os.path.join('/app/downloads', media_post.media_url)
                
                # Добавляем image frame с абсолютным путем и border_width
                if os.path.exists(image_path):
                    print(f"✅ Adding image: {image_path} (border: {border_width_px}px = {border_width_pt:.2f}pt)")
                    self.add_image_frame(
                        image_path, 
                        media_frame_bounds, 
                        page_index=page_number - 1,
                        stroke_weight=border_width_pt
                    )
                else:
                    print(f"⚠️ Image not found: {image_path}")
    
    def save(self, output_path):
        """
        Сохраняет IDML документ
        
        :param output_path: путь для сохранения .idml файла
        :return: путь к созданному файлу
        """
        # Создаем временную директорию для сборки
        temp_dir = f'/tmp/idml_build_{uuid.uuid4().hex}'
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Генерируем XML файлы
            self._generate_mimetype(temp_dir)
            self._generate_meta_inf(temp_dir)
            self._generate_xml_backing(temp_dir)
            self._generate_designmap(temp_dir)
            self._generate_styles(temp_dir)
            self._generate_resources(temp_dir)
            self._generate_spreads(temp_dir)
            self._generate_stories(temp_dir)
            
            # Медиа-файлы используют абсолютные пути, копировать не нужно
            print(f"\n📎 Using {len(self.links)} external image links")
            
            # Создаем ZIP архив (IDML)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as idml_zip:
                # mimetype должен быть первым и без компрессии
                idml_zip.write(
                    os.path.join(temp_dir, 'mimetype'),
                    'mimetype',
                    compress_type=zipfile.ZIP_STORED
                )
                
                # Остальные файлы
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file == 'mimetype':
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        idml_zip.write(file_path, arcname)
            
            return output_path
            
        finally:
            # Очистка временных файлов
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def _generate_mimetype(self, temp_dir):
        """Создает файл mimetype"""
        with open(os.path.join(temp_dir, 'mimetype'), 'w') as f:
            f.write('application/vnd.adobe.indesign-idml-package')
    
    def _generate_designmap(self, temp_dir):
        """Создает designmap.xml"""
        nsmap = {
            'idPkg': 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging'
        }
        root = ET.Element('Document', nsmap=nsmap)
        root.set('DOMVersion', '17.0')
        root.set('Self', 'd')
        root.set('StoryList', 'ub0')
        root.set('Name', f'{self.channel.name}.idml')
        root.set('ZeroPoint', '0 0')
        root.set('ActiveLayer', 'u1')
        
        # Namespace для idPkg элементов
        idPkg_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
        
        # Language (обязательный элемент)
        ET.SubElement(root, 'Language',
                     Self='Language/$ID/English%3a USA',
                     Name='$ID/English: USA',
                     SingleQuotes="''",
                     DoubleQuotes='""',
                     PrimaryLanguageName='$ID/English',
                     SublanguageName='$ID/USA',
                     Id='269',
                     HyphenationVendor='Hunspell',
                     SpellingVendor='Hunspell')
        
        # Resources
        ET.SubElement(root, f'{idPkg_ns}Graphic', src='Resources/Graphic.xml')
        ET.SubElement(root, f'{idPkg_ns}Fonts', src='Resources/Fonts.xml')
        ET.SubElement(root, f'{idPkg_ns}Styles', src='Resources/Styles.xml')
        
        # NumberingList
        ET.SubElement(root, 'NumberingList',
                     Self='NumberingList/$ID/[Default]',
                     Name='$ID/[Default]',
                     ContinueNumbersAcrossStories='false',
                     ContinueNumbersAcrossDocuments='false')
        
        # Preferences
        ET.SubElement(root, f'{idPkg_ns}Preferences', src='Resources/Preferences.xml')
        
        # Tags
        ET.SubElement(root, f'{idPkg_ns}Tags', src='XML/Tags.xml')
        
        # Layer (обязательный элемент)
        layer = ET.SubElement(root, 'Layer',
                             Self='u1',
                             Name='Layer 1',
                             Visible='true',
                             Locked='false',
                             IgnoreWrap='false',
                             ShowGuides='true',
                             LockGuides='false',
                             UI='true',
                             Expendable='true',
                             Printable='true')
        props = ET.SubElement(layer, 'Properties')
        color = ET.SubElement(props, 'LayerColor', type='enumeration')
        color.text = 'LightBlue'
        
        # Список всех Spreads
        for spread in self.spreads:
            ET.SubElement(root, f'{idPkg_ns}Spread', src=f'Spreads/{spread["id"]}.xml')
        
        # Список всех Stories
        for story in self.stories:
            ET.SubElement(root, f'{idPkg_ns}Story', src=f'Stories/{story["id"]}.xml')
        
        # BackingStory
        ET.SubElement(root, f'{idPkg_ns}BackingStory', src='XML/BackingStory.xml')
        
        xml_str = ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        
        with open(os.path.join(temp_dir, 'designmap.xml'), 'wb') as f:
            # Добавляем <?aid ?> директиву после XML declaration
            aid_directive = b'<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="17.4(51)" ?>\n'
            lines = xml_str.split(b'\n', 1)
            f.write(lines[0] + b'\n' + aid_directive + lines[1])
    
    def _generate_styles(self, temp_dir):
        """Создает Resources/Styles.xml"""
        os.makedirs(os.path.join(temp_dir, 'Resources'), exist_ok=True)
        
        styles_xml = generate_styles_xml()
        
        with open(os.path.join(temp_dir, 'Resources', 'Styles.xml'), 'wb') as f:
            f.write(styles_xml)
    
    def _generate_resources(self, temp_dir):
        """Создает остальные Resources файлы"""
        resources_dir = os.path.join(temp_dir, 'Resources')
        os.makedirs(resources_dir, exist_ok=True)
        
        # Fonts.xml
        fonts_xml = generate_fonts_xml()
        with open(os.path.join(resources_dir, 'Fonts.xml'), 'wb') as f:
            f.write(fonts_xml)
        
        # Graphic.xml
        graphic_xml = generate_graphic_xml()
        with open(os.path.join(resources_dir, 'Graphic.xml'), 'wb') as f:
            f.write(graphic_xml)
        
        # Preferences.xml
        prefs_xml = generate_preferences_xml()
        with open(os.path.join(resources_dir, 'Preferences.xml'), 'wb') as f:
            f.write(prefs_xml)
    
    def _generate_spreads(self, temp_dir):
        """Создает Spreads/*.xml"""
        os.makedirs(os.path.join(temp_dir, 'Spreads'), exist_ok=True)
        
        for spread in self.spreads:
            spread_xml = self._create_spread_xml(spread)
            
            with open(os.path.join(temp_dir, 'Spreads', f"{spread['id']}.xml"), 'wb') as f:
                f.write(spread_xml)
    
    def _create_spread_xml(self, spread):
        """Создает XML для одного Spread по модели InDesign"""
        page_count = spread.get('page_count', len(spread['pages']))
        binding_location = spread.get('binding_location', 0)
        item_transform = spread.get('item_transform', '1 0 0 1 0 0')
        
        root = ET.Element('Spread', 
                         Self=spread['id'],
                         PageCount=str(page_count),
                         BindingLocation=str(binding_location),
                         ItemTransform=item_transform,
                         FlattenerOverride='Default',
                         nsmap={
            None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
        })
        
        # FlattenerPreference (требуется InDesign)
        ET.SubElement(root, 'FlattenerPreference')
        
        for page in spread['pages']:
            page_item_transform = page.get('item_transform', '1 0 0 1 0 0')
            page_name = page.get('name', '1')
            
            page_elem = ET.SubElement(root, 'Page',
                                     Self=page['id'],
                                     Name=page_name,
                                     GeometricBounds=' '.join(map(str, page['bounds'])),
                                     ItemTransform=page_item_transform)
            
            # Добавляем MarginPreference с нашими полями
            # margins уже в points из __init__
            top_margin = self.settings['margins'][0]
            left_margin = self.settings['margins'][1]
            bottom_margin = self.settings['margins'][2]
            right_margin = self.settings['margins'][3]
            
            ET.SubElement(page_elem, 'MarginPreference',
                         ColumnCount='1',
                         ColumnGutter='12',
                         Top=str(top_margin),
                         Bottom=str(bottom_margin),
                         Left=str(left_margin),
                         Right=str(right_margin),
                         ColumnDirection='Horizontal',
                         ColumnsPositions=f'0 {self.page_width - left_margin - right_margin}')
            
            # Добавляем фреймы
            for frame in page['frames']:
                if frame['type'] == 'TextFrame':
                    self._create_text_frame_elem(page_elem, frame, page)
                elif frame['type'] == 'Rectangle':
                    self._create_image_frame_elem(page_elem, frame, page)
        
        return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    def _calculate_item_transform(self, bounds, page):
        """
        Вычисляет ItemTransform и PathPoints для элемента (текст или изображение)
        
        :param bounds: [y1, x1, y2, x2] - абсолютные координаты на странице
        :param page: объект страницы с 'name' (номер страницы)
        :return: (item_transform, path_points) - строка transform и список точек
        """
        y1, x1, y2, x2 = bounds
        
        # Вычисляем центр фрейма от верхнего левого угла
        center_x = (x1 + x2) / 2
        center_y_from_top = (y1 + y2) / 2
        
        # Вычисляем размеры фрейма
        width = x2 - x1
        height = y2 - y1
        
        # InDesign: X от левого края, Y от центра страницы
        page_height = self.page_height
        center_y = center_y_from_top - (page_height / 2)
        
        # Для четных страниц (левая сторона разворота) добавляем offset
        page_number = int(page['name'])
        if page_number > 1 and page_number % 2 == 0:
            # Левая страница разворота - сдвигаем влево на ширину страницы
            center_x = center_x - self.page_width
        
        # ItemTransform задает позицию центра фрейма
        item_transform = f'1 0 0 1 {center_x} {center_y}'
        
        # PathPoints относительно центра фрейма (симметричные координаты)
        half_width = width / 2
        half_height = height / 2
        
        path_points = [
            (-half_width, -half_height),  # top-left
            (half_width, -half_height),   # top-right
            (half_width, half_height),    # bottom-right
            (-half_width, half_height)    # bottom-left
        ]
        
        return item_transform, path_points
    
    def _create_text_frame_elem(self, parent, frame, page):
        """Создает TextFrame элемент по модели InDesign"""
        # Используем утилиту для вычисления позиции
        item_transform, path_points = self._calculate_item_transform(frame['bounds'], page)
        
        # Получаем vertical_justification из данных фрейма (по умолчанию TopAlign)
        vertical_justification = frame.get('vertical_justification', 'TopAlign')
        
        text_frame = ET.SubElement(parent, 'TextFrame',
                                   Self=frame['id'],
                                   ParentStory=frame['story_id'],
                                   GeometricBounds=' '.join(map(str, frame['bounds'])),
                                   ItemTransform=item_transform,
                                   ContentType='TextType')
        
        # Properties с PathGeometry и TextFramePreference
        props = ET.SubElement(text_frame, 'Properties')
        
        # TextFramePreference для вертикального выравнивания
        text_frame_pref = ET.SubElement(props, 'TextFramePreference')
        ET.SubElement(text_frame_pref, 'Properties')
        text_frame_pref.set('VerticalJustification', vertical_justification)
        
        # PathGeometry (обязательно для InDesign)
        path_geo = ET.SubElement(props, 'PathGeometry')
        geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
        path_points_array = ET.SubElement(geo_path, 'PathPointArray')
        
        for x, y in path_points:
            anchor = f'{x} {y}'
            ET.SubElement(path_points_array, 'PathPointType',
                         Anchor=anchor,
                         LeftDirection=anchor,
                         RightDirection=anchor)
        
        return text_frame
    
    def _create_image_frame_elem(self, parent, frame, page):
        """Создает Rectangle с Image элемент"""
        # Используем ту же утилиту для вычисления позиции
        item_transform, path_points = self._calculate_item_transform(frame['bounds'], page)
        
        # Получаем stroke_weight из данных фрейма (в points)
        stroke_weight = frame.get('stroke_weight', 0)
        # Используем Color/Borders для белого цвета рамки
        stroke_color = 'Color/Borders' if stroke_weight > 0 else 'Swatch/None'
        
        # Получаем corner_radius из данных фрейма (в points)
        corner_radius = frame.get('corner_radius', 0)
        
        # Атрибуты Rectangle
        rect_attrs = {
            'Self': frame['id'],
            'GeometricBounds': ' '.join(map(str, frame['bounds'])),
            'ItemTransform': item_transform,
            'FillColor': 'Swatch/None',
            'StrokeWeight': str(stroke_weight),
            'StrokeColor': stroke_color,
            'ContentType': 'GraphicType'
        }
        
        # Добавляем StrokeAlignment для имитации CSS border (inside)
        if stroke_weight > 0:
            rect_attrs['StrokeAlignment'] = 'InsideAlignment'
        
        # Добавляем CornerRadius для скругления углов
        if corner_radius > 0:
            # CornerOption - правильный способ задать скругление в IDML
            rect_attrs['TopLeftCornerOption'] = 'RoundedCorner'
            rect_attrs['TopRightCornerOption'] = 'RoundedCorner'
            rect_attrs['BottomLeftCornerOption'] = 'RoundedCorner'
            rect_attrs['BottomRightCornerOption'] = 'RoundedCorner'
            rect_attrs['TopLeftCornerRadius'] = str(corner_radius)
            rect_attrs['TopRightCornerRadius'] = str(corner_radius)
            rect_attrs['BottomLeftCornerRadius'] = str(corner_radius)
            rect_attrs['BottomRightCornerRadius'] = str(corner_radius)
        
        rect = ET.SubElement(parent, 'Rectangle', **rect_attrs)
        
        # Properties с PathGeometry
        props = ET.SubElement(rect, 'Properties')
        path_geo = ET.SubElement(props, 'PathGeometry')
        geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
        path_points_array = ET.SubElement(geo_path, 'PathPointArray')
        
        # Используем path_points из утилиты (относительные к центру)
        for x, y in path_points:
            anchor = f'{x} {y}'
            ET.SubElement(path_points_array, 'PathPointType',
                         Anchor=anchor,
                         LeftDirection=anchor,
                         RightDirection=anchor)
        
        # FrameFittingOption идет после Properties (на уровне Rectangle, не Image!)
        ET.SubElement(rect, 'FrameFittingOption',
                     AutoFit='true',
                     LeftCrop='0',
                     TopCrop='0',
                     RightCrop='0',
                     BottomCrop='0',
                     FittingOnEmptyFrame='FillProportionally',
                     FittingAlignment='CenterAnchor')
        
        # Добавляем Image
        if 'image' in frame:
            image = ET.SubElement(rect, 'Image',
                                 Self=self.next_id('image_'),
                                 ItemTransform='1 0 0 1 0 0')
            
            # Link с абсолютным путем
            link = ET.SubElement(image, 'Link',
                               Self=frame['image']['link_id'],
                               LinkResourceURI=f"file://{frame['image']['path']}")
        
        return rect
    
    def _generate_stories(self, temp_dir):
        """Создает Stories/*.xml"""
        os.makedirs(os.path.join(temp_dir, 'Stories'), exist_ok=True)
        
        for story in self.stories:
            story_xml = self._create_story_xml(story)
            
            with open(os.path.join(temp_dir, 'Stories', f"{story['id']}.xml"), 'wb') as f:
                f.write(story_xml)
    
    def _create_story_xml(self, story):
        """Создает XML для одной Story с поддержкой параграфов"""
        root = ET.Element('Story',
                         Self=story['id'],
                         AppliedTOCStyle='n',
                         TrackChanges='false',
                         nsmap={None: 'http://ns.adobe.com/AdobeInDesign/4.0/'})
        
        # StoryPreference
        ET.SubElement(root, 'StoryPreference',
                     OpticalMarginAlignment='false',
                     OpticalMarginSize='12')
        
        # Парсим HTML и создаем ParagraphStyleRange для каждого параграфа
        self._add_formatted_content(root, story['content'], story['style'])
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        return ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    def _add_formatted_content(self, parent, html_content, style='PostBody'):
        """
        Парсит HTML контент и добавляет ParagraphStyleRange для каждого параграфа
        Поддерживает теги: <p> (параграфы), strong (bold), em (italic), del (strikethrough), br (перенос)
        """
        from bs4 import BeautifulSoup
        import logging
        
        # Парсим HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ищем все параграфы <p>
        paragraphs = soup.find_all('p')
        
        if paragraphs:
            # Есть параграфы - обрабатываем каждый отдельно
            logging.info(f"[IDML] Найдено {len(paragraphs)} параграфов в HTML")
            for para in paragraphs:
                # Проверяем атрибут style у параграфа (для переопределения стиля)
                para_style = para.get('style', style)
                
                # Создаем ParagraphStyleRange для каждого параграфа
                para_range = ET.SubElement(parent, 'ParagraphStyleRange',
                                          AppliedParagraphStyle=f'ParagraphStyle/{para_style}')
                
                # Обрабатываем содержимое параграфа, передаем para_style как char_style
                self._process_element(para_range, para, char_style=para_style)
                
                # Добавляем символ конца параграфа (перенос)
                self._add_paragraph_break(para_range)
        else:
            # Нет параграфов - обрабатываем как один блок (обратная совместимость)
            logging.info(f"[IDML] Нет параграфов <p>, обрабатываем как единый текст")
            para_range = ET.SubElement(parent, 'ParagraphStyleRange',
                                      AppliedParagraphStyle=f'ParagraphStyle/{style}')
            self._process_element(para_range, soup, char_style=style)
    
    def _process_element(self, parent, element, char_style='PostBody'):
        """Рекурсивно обрабатывает элементы и добавляет CharacterStyleRange"""
        from bs4 import NavigableString
        
        # Если это текстовый узел
        if isinstance(element, NavigableString):
            text = str(element)
            if text.strip():  # Игнорируем пустые текстовые узлы
                self._add_character_range(parent, text, {}, char_style)
            return
        
        # Пропускаем обработку тега <p> (он обрабатывается на уровень выше)
        if element.name == 'p':
            # Обрабатываем дочерние элементы параграфа
            for child in element.children:
                self._process_element(parent, child, char_style)
            return
        
        # Обработка <br> - добавляем перенос строки
        if element.name == 'br':
            self._add_line_break(parent)
            return
        
        # Определяем стиль на основе тега
        properties = {}
        
        if element.name == 'strong' or element.name == 'b':
            properties['FontStyle'] = 'Bold'
        elif element.name == 'em' or element.name == 'i':
            properties['FontStyle'] = 'Italic'
        elif element.name == 'del' or element.name == 's':
            properties['StrikeThru'] = 'true'
        
        # Если есть свойства форматирования, оборачиваем в CharacterStyleRange
        if properties:
            # Получаем весь текст внутри элемента (включая вложенные теги)
            text = element.get_text()
            if text.strip():
                self._add_character_range(parent, text, properties, char_style)
        else:
            # Иначе обрабатываем дочерние элементы
            for child in element.children:
                self._process_element(parent, child, char_style)
    
    def _add_character_range(self, parent, text, properties, char_style='PostBody'):
        """Добавляет CharacterStyleRange с заданными свойствами"""
        # Если нет форматирования, применяем Character Style
        if not properties:
            char_range = ET.SubElement(parent, 'CharacterStyleRange',
                                       AppliedCharacterStyle=f'CharacterStyle/{char_style}')
        else:
            # Для форматированного текста - default + Properties
            char_range = ET.SubElement(parent, 'CharacterStyleRange',
                                       AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
            # Добавляем Properties с форматированием + базовым шрифтом
            props_elem = ET.SubElement(char_range, 'Properties')
            # Сначала добавляем базовый шрифт
            ET.SubElement(props_elem, 'AppliedFont', type='string').text = FONTS['body']
            # Потом форматирование (FontStyle будет "Bold", "Italic" и т.д.)
            for key, value in properties.items():
                ET.SubElement(props_elem, key, type='string').text = value
        
        # Content
        content_elem = ET.SubElement(char_range, 'Content')
        content_elem.text = text
    
    def _add_line_break(self, parent):
        """Добавляет перенос строки (Br)"""
        char_range = ET.SubElement(parent, 'CharacterStyleRange',
                                   AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
        ET.SubElement(char_range, 'Br')
    
    def _add_paragraph_break(self, parent):
        """Добавляет конец параграфа"""
        char_range = ET.SubElement(parent, 'CharacterStyleRange',
                                   AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
        content_elem = ET.SubElement(char_range, 'Content')
        content_elem.text = '\r'  # Символ конца параграфа в IDML
    
    def _generate_meta_inf(self, temp_dir):
        """Создает META-INF/container.xml и metadata.xml"""
        meta_inf_dir = os.path.join(temp_dir, 'META-INF')
        os.makedirs(meta_inf_dir, exist_ok=True)
        
        # container.xml
        container_ns = 'urn:oasis:names:tc:opendocument:xmlns:container'
        container = ET.Element('container', version='1.0', xmlns=container_ns)
        rootfiles = ET.SubElement(container, 'rootfiles')
        ET.SubElement(rootfiles, 'rootfile', 
                     {'full-path': 'designmap.xml', 'media-type': 'text/xml'})
        
        tree = ET.ElementTree(container)
        ET.indent(tree, space='  ')
        tree.write(
            os.path.join(meta_inf_dir, 'container.xml'),
            encoding='UTF-8',
            xml_declaration=True,
            standalone='yes'
        )
        
        # metadata.xml (упрощенная версия с XMP)
        metadata_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.2-c000 79.1b65a79, 2022/06/13-17:46:14">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
            xmlns:idPriv="http://ns.adobe.com/xmp/InDesign/private">
         <dc:format>application/x-indesign</dc:format>
         <xmp:CreateDate>{datetime.now().isoformat()}</xmp:CreateDate>
         <xmp:MetadataDate>{datetime.now().isoformat()}</xmp:MetadataDate>
         <xmp:ModifyDate>{datetime.now().isoformat()}</xmp:ModifyDate>
         <xmp:CreatorTool>TG Offliner IDML Export</xmp:CreatorTool>
         <xmpMM:InstanceID>xmp.iid:{uuid.uuid4()}</xmpMM:InstanceID>
         <xmpMM:DocumentID>xmp.did:{uuid.uuid4()}</xmpMM:DocumentID>
         <xmpMM:OriginalDocumentID>xmp.did:{uuid.uuid4()}</xmpMM:OriginalDocumentID>
         <xmpMM:RenditionClass>default</xmpMM:RenditionClass>
         <idPriv:DocChangeCount>1</idPriv:DocChangeCount>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>
<?xpacket end="r"?>'''
        
        with open(os.path.join(meta_inf_dir, 'metadata.xml'), 'w', encoding='utf-8') as f:
            f.write(metadata_content)
    
    def _generate_xml_backing(self, temp_dir):
        """Создает XML/BackingStory.xml и Tags.xml"""
        xml_dir = os.path.join(temp_dir, 'XML')
        os.makedirs(xml_dir, exist_ok=True)
        
        # BackingStory.xml
        idPkg_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
        backing_root = ET.Element(f'{idPkg_ns}BackingStory', DOMVersion='17.0')
        
        xml_story = ET.SubElement(backing_root, 'XmlStory',
                                 Self='ub0',
                                 UserText='true',
                                 IsEndnoteStory='false',
                                 AppliedTOCStyle='n',
                                 TrackChanges='false',
                                 StoryTitle='$ID/',
                                 AppliedNamedGrid='n')
        
        para_range = ET.SubElement(xml_story, 'ParagraphStyleRange',
                                  AppliedParagraphStyle='ParagraphStyle/$ID/NormalParagraphStyle')
        
        char_range = ET.SubElement(para_range, 'CharacterStyleRange',
                                  AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
        
        ET.SubElement(char_range, 'XMLElement',
                     Self='di2',
                     MarkupTag='XMLTag/Root')
        
        content = ET.SubElement(char_range, 'Content')
        content.text = ''
        
        tree = ET.ElementTree(backing_root)
        ET.indent(tree, space='  ')
        tree.write(
            os.path.join(xml_dir, 'BackingStory.xml'),
            encoding='UTF-8',
            xml_declaration=True,
            standalone='yes'
        )
        
        # Tags.xml
        tags_root = ET.Element(f'{idPkg_ns}Tags', DOMVersion='17.0')
        xml_tag = ET.SubElement(tags_root, 'XMLTag', Self='XMLTag/Root', Name='Root')
        properties = ET.SubElement(xml_tag, 'Properties')
        tag_color = ET.SubElement(properties, 'TagColor', type='enumeration')
        tag_color.text = 'LightBlue'
        
        tree = ET.ElementTree(tags_root)
        ET.indent(tree, space='  ')
        tree.write(
            os.path.join(xml_dir, 'Tags.xml'),
            encoding='UTF-8',
            xml_declaration=True,
            standalone='yes'
        )
