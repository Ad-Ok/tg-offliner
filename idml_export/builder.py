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

from .constants import PAGE_SIZES, DEFAULT_PRINT_SETTINGS, DEFAULT_POST_SETTINGS, mm_to_points
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
            spread = {
                'id': spread_id,
                'pages': [new_page],
                'page_count': 1,  # Пока одна страница, будет 2 после добавления правой
                'binding_location': 1,  # Разворот
                'item_transform': f'1 0 0 1 0 {self.page_height + center_offset}'  # Сдвиг разворота вниз
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
    
    def add_text_frame(self, story_id, bounds, page_index=None):
        """
        Добавляет текстовый фрейм на страницу
        
        :param story_id: ID Story
        :param bounds: [y1, x1, y2, x2]
        :param page_index: индекс страницы (0-based), если None - текущая страница
        """
        frame_id = self.next_id('frame_')
        
        frame = {
            'id': frame_id,
            'type': 'TextFrame',
            'story_id': story_id,
            'bounds': bounds
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
    
    def add_image_frame(self, image_path, bounds, link_in_package=True, page_index=None, relative_path=None):
        """
        Добавляет фрейм с изображением
        
        :param image_path: путь к изображению (относительный или абсолютный)
        :param bounds: [y1, x1, y2, x2]
        :param link_in_package: если True, копирует файл в IDML пакет
        :param page_index: индекс страницы (0-based), если None - текущая страница
        :param relative_path: относительный путь для Links (channel_id/media/file.jpg)
        """
        frame_id = self.next_id('frame_')
        link_id = self.next_id('link_')
        
        # Используем relative_path если передан, иначе только имя файла
        if relative_path:
            link_path = f"Links/{relative_path}"
        else:
            image_filename = os.path.basename(image_path)
            link_path = f"Links/{image_filename}"
        
        frame = {
            'id': frame_id,
            'type': 'Rectangle',
            'bounds': bounds,
            'image': {
                'link_id': link_id,
                'path': link_path  # Путь внутри IDML пакета
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
            'path': link_path
        })
        
        # Добавляем файл для копирования в пакет
        if link_in_package and os.path.exists(image_path):
            self.media_files.append({
                'source': image_path,
                'dest': link_path  # Полный путь с Links/ префиксом
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
        
        # Добавляем текст если есть
        if post.message:
            # Используем исходный текст из базы (с HTML форматированием)
            story_id = self.add_text_story(post.message, 'PostBody')
            self.add_text_frame(story_id, frame_bounds, page_index=page_number - 1)
        
        # Добавляем медиа элементы
        media_elements = post_data.get('media', [])
        for media_elem in media_elements:
            if media_elem['type'] == 'image' and post.media_url:
                # Проверяем media_type - только фото, не веб-страницы
                if post.media_type not in ['MessageMediaPhoto', 'MessageMediaDocument']:
                    continue
                
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
                image_path = os.path.join('/app/downloads', post.media_url)
                
                # Добавляем image frame с относительным путем
                if os.path.exists(image_path):
                    # relative_path сохраняет структуру: channel_id/media/file.jpg
                    self.add_image_frame(
                        image_path, 
                        media_frame_bounds, 
                        page_index=page_number - 1,
                        relative_path=post.media_url  # channel_id/media/file.jpg
                    )
    
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
            
            # Копируем медиа-файлы в папку Links с сохранением структуры
            if self.media_files:
                for media in self.media_files:
                    source_path = media['source']
                    # dest уже содержит Links/ префикс
                    dest_relative = media['dest']  # Links/channel_id/media/file.jpg
                    dest_path = os.path.join(temp_dir, dest_relative)
                    
                    # Создаем подпапки если нужно
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
            
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
                    self._create_image_frame_elem(page_elem, frame)
        
        return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    def _create_text_frame_elem(self, parent, frame, page):
        """Создает TextFrame элемент по модели InDesign"""
        # bounds это [y1, x1, y2, x2] - абсолютные координаты на странице
        y1, x1, y2, x2 = frame['bounds']
        
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
        
        text_frame = ET.SubElement(parent, 'TextFrame',
                                   Self=frame['id'],
                                   ParentStory=frame['story_id'],
                                   GeometricBounds=' '.join(map(str, frame['bounds'])),
                                   ItemTransform=item_transform,
                                   ContentType='TextType')
        
        # Properties с PathGeometry (обязательно для InDesign)
        props = ET.SubElement(text_frame, 'Properties')
        path_geo = ET.SubElement(props, 'PathGeometry')
        geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
        path_points = ET.SubElement(geo_path, 'PathPointArray')
        
        # PathPoints относительно центра фрейма (симметричные координаты)
        half_width = width / 2
        half_height = height / 2
        
        corners = [
            (-half_width, -half_height),  # top-left
            (half_width, -half_height),   # top-right
            (half_width, half_height),    # bottom-right
            (-half_width, half_height)    # bottom-left
        ]
        
        for x, y in corners:
            anchor = f'{x} {y}'
            ET.SubElement(path_points, 'PathPointType',
                         Anchor=anchor,
                         LeftDirection=anchor,
                         RightDirection=anchor)
        
        return text_frame
    
    def _create_image_frame_elem(self, parent, frame):
        """Создает Rectangle с Image элемент"""
        rect = ET.SubElement(parent, 'Rectangle',
                            Self=frame['id'],
                            GeometricBounds=' '.join(map(str, frame['bounds'])),
                            ItemTransform='1 0 0 1 0 0')
        
        # Properties с PathGeometry
        props = ET.SubElement(rect, 'Properties')
        path_geo = ET.SubElement(props, 'PathGeometry')
        geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
        path_points = ET.SubElement(geo_path, 'PathPointArray')
        
        # Добавляем 4 точки прямоугольника
        y1, x1, y2, x2 = frame['bounds']
        corners = [
            (y1, x1), (y1, x2), (y2, x2), (y2, x1)
        ]
        for y, x in corners:
            anchor = f'{y} {x}'
            ET.SubElement(path_points, 'PathPointType',
                         Anchor=anchor,
                         LeftDirection=anchor,
                         RightDirection=anchor)
        
        # Добавляем Image
        if 'image' in frame:
            image = ET.SubElement(rect, 'Image', Self=self.next_id('image_'))
            # Используем относительный путь внутри IDML пакета
            link = ET.SubElement(image, 'Link',
                               Self=frame['image']['link_id'],
                               LinkResourceURI=f"file:{frame['image']['path']}")
        
        return rect
    
    def _generate_stories(self, temp_dir):
        """Создает Stories/*.xml"""
        os.makedirs(os.path.join(temp_dir, 'Stories'), exist_ok=True)
        
        for story in self.stories:
            story_xml = self._create_story_xml(story)
            
            with open(os.path.join(temp_dir, 'Stories', f"{story['id']}.xml"), 'wb') as f:
                f.write(story_xml)
    
    def _create_story_xml(self, story):
        """Создает XML для одной Story"""
        root = ET.Element('Story',
                         Self=story['id'],
                         AppliedTOCStyle='n',
                         TrackChanges='false',
                         nsmap={None: 'http://ns.adobe.com/AdobeInDesign/4.0/'})
        
        # StoryPreference
        ET.SubElement(root, 'StoryPreference',
                     OpticalMarginAlignment='false',
                     OpticalMarginSize='12')
        
        # ParagraphStyleRange
        para_range = ET.SubElement(root, 'ParagraphStyleRange',
                                   AppliedParagraphStyle=f'ParagraphStyle/{story["style"]}')
        
        # Парсим HTML и создаем CharacterStyleRange для каждого фрагмента
        self._add_formatted_content(para_range, story['content'])
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        return ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    def _add_formatted_content(self, parent, html_content):
        """
        Парсит HTML контент и добавляет CharacterStyleRange с форматированием
        Поддерживает теги: strong (bold), em (italic), del (strikethrough)
        """
        from bs4 import BeautifulSoup
        
        # Парсим HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Рекурсивно обходим элементы
        self._process_element(parent, soup)
    
    def _process_element(self, parent, element):
        """Рекурсивно обрабатывает элементы и добавляет CharacterStyleRange"""
        from bs4 import NavigableString
        
        # Если это текстовый узел
        if isinstance(element, NavigableString):
            text = str(element)
            if text.strip():  # Игнорируем пустые текстовые узлы
                self._add_character_range(parent, text, {})
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
                self._add_character_range(parent, text, properties)
        else:
            # Иначе обрабатываем дочерние элементы
            for child in element.children:
                self._process_element(parent, child)
    
    def _add_character_range(self, parent, text, properties):
        """Добавляет CharacterStyleRange с заданными свойствами"""
        char_range = ET.SubElement(parent, 'CharacterStyleRange',
                                   AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
        
        # Добавляем Properties если есть форматирование
        if properties:
            props_elem = ET.SubElement(char_range, 'Properties')
            for key, value in properties.items():
                ET.SubElement(props_elem, key).text = value
        
        # Content
        content_elem = ET.SubElement(char_range, 'Content')
        content_elem.text = text
    
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
