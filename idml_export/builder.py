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
        """Создает базовый документ с одним Spread"""
        # Размер страницы из констант (в мм), конвертируем в points
        page_size_mm = PAGE_SIZES[self.settings['page_size']]
        width = mm_to_points(page_size_mm['width'])
        height = mm_to_points(page_size_mm['height'])
        
        # Создаем первый Spread
        spread_id = self.next_id('spread_')
        page_id = self.next_id('page_')
        
        spread = {
            'id': spread_id,
            'pages': [{
                'id': page_id,
                'bounds': [0, 0, height, width],
                'frames': []
            }]
        }
        
        self.spreads.append(spread)
        self.current_page = spread['pages'][0]
        
        # Вычисляем границы текстовой области
        text_area = calculate_text_frame_bounds(
            self.current_page['bounds'],
            self.settings['margins'],
            self.settings['text_columns'],
            self.settings['column_gutter']
        )
        
        self.current_y = text_area['bounds'][0]  # Начинаем с верха текстовой области
        
        return spread
    
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
    
    def add_text_frame(self, story_id, bounds):
        """
        Добавляет текстовый фрейм на текущую страницу
        
        :param story_id: ID Story
        :param bounds: [y1, x1, y2, x2]
        """
        frame_id = self.next_id('frame_')
        
        frame = {
            'id': frame_id,
            'type': 'TextFrame',
            'story_id': story_id,
            'bounds': bounds
        }
        
        self.current_page['frames'].append(frame)
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
    
    def add_image_frame(self, image_path, bounds, link_in_package=True):
        """
        Добавляет фрейм с изображением
        
        :param image_path: путь к изображению (относительный или абсолютный)
        :param bounds: [y1, x1, y2, x2]
        :param link_in_package: если True, копирует файл в IDML пакет
        """
        frame_id = self.next_id('frame_')
        link_id = self.next_id('link_')
        
        # Имя файла для ссылки в IDML
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
        
        self.current_page['frames'].append(frame)
        
        # Добавляем ссылку в список
        self.links.append({
            'id': link_id,
            'path': link_path
        })
        
        # Добавляем файл для копирования в пакет
        if link_in_package and os.path.exists(image_path):
            self.media_files.append({
                'source': image_path,
                'dest': link_path
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
            
            # Копируем медиа-файлы в папку Links
            if self.media_files:
                links_dir = os.path.join(temp_dir, 'Links')
                os.makedirs(links_dir, exist_ok=True)
                
                for media in self.media_files:
                    source_path = media['source']
                    dest_filename = os.path.basename(media['dest'])
                    dest_path = os.path.join(links_dir, dest_filename)
                    
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
        """Создает XML для одного Spread"""
        root = ET.Element('Spread', Self=spread['id'], 
                         FlattenerOverride='Default',
                         nsmap={
            None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
        })
        
        # FlattenerPreference (требуется InDesign)
        ET.SubElement(root, 'FlattenerPreference')
        
        for page in spread['pages']:
            page_elem = ET.SubElement(root, 'Page',
                                     Self=page['id'],
                                     GeometricBounds=' '.join(map(str, page['bounds'])),
                                     ItemTransform='1 0 0 1 0 0')
            
            # Добавляем фреймы
            for frame in page['frames']:
                if frame['type'] == 'TextFrame':
                    self._create_text_frame_elem(page_elem, frame)
                elif frame['type'] == 'Rectangle':
                    self._create_image_frame_elem(page_elem, frame)
        
        return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    def _create_text_frame_elem(self, parent, frame):
        """Создает TextFrame элемент"""
        text_frame = ET.SubElement(parent, 'TextFrame',
                                   Self=frame['id'],
                                   ParentStory=frame['story_id'],
                                   GeometricBounds=' '.join(map(str, frame['bounds'])),
                                   ItemTransform='1 0 0 1 0 0',
                                   ContentType='TextType')
        
        # Properties с PathGeometry (обязательно для InDesign)
        props = ET.SubElement(text_frame, 'Properties')
        path_geo = ET.SubElement(props, 'PathGeometry')
        geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
        path_points = ET.SubElement(geo_path, 'PathPointArray')
        
        # Добавляем 4 точки прямоугольника
        # bounds это [y1, x1, y2, x2], но PathPointType координаты должны быть "x y"
        y1, x1, y2, x2 = frame['bounds']
        corners = [
            (x1, y1),  # top-left
            (x2, y1),  # top-right
            (x2, y2),  # bottom-right
            (x1, y2)   # bottom-left
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
        
        # CharacterStyleRange
        char_range = ET.SubElement(para_range, 'CharacterStyleRange',
                                   AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
        
        # Content
        content_elem = ET.SubElement(char_range, 'Content')
        content_elem.text = story['content']
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        return ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
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
