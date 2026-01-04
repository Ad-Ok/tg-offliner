"""
Генерация Styles.xml для IDML документа
Содержит Paragraph Styles, Character Styles, Object Styles
"""

from lxml import etree as ET
from .constants import FONTS


def generate_styles_xml():
    """
    Генерирует Styles.xml с определениями всех стилей
    """
    # Namespaces
    nsmap = {
        'idPkg': 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging',
        None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
    }
    idPkg_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
    
    # Root element
    root = ET.Element(f'{idPkg_ns}Styles', nsmap=nsmap)
    
    # RootCharacterStyleGroup
    char_style_group = ET.SubElement(root, 'RootCharacterStyleGroup', Self='character-style-group-root')
    _create_character_styles(char_style_group)
    
    # RootParagraphStyleGroup
    para_style_group = ET.SubElement(root, 'RootParagraphStyleGroup', Self='paragraph-style-group-root')
    _create_paragraph_styles(para_style_group)
    
    # RootObjectStyleGroup
    obj_style_group = ET.SubElement(root, 'RootObjectStyleGroup', Self='object-style-group-root')
    _create_object_styles(obj_style_group)
    
    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def _create_character_styles(parent):
    """Создает Character Styles"""
    
    # Default [No character style]
    ET.SubElement(parent, 'CharacterStyle',
                  Self='CharacterStyle/$ID/[No character style]',
                  Name='$ID/[No character style]')
    
    # PostDate - стиль для даты (10pt)
    post_date_style = ET.SubElement(parent, 'CharacterStyle',
                                    Self='CharacterStyle/PostDate',
                                    Name='PostDate')
    props = ET.SubElement(post_date_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = FONTS['body']
    ET.SubElement(props, 'PointSize', type='double').text = '10'
    ET.SubElement(props, 'FillColor', type='string').text = 'Color/Gray'
    
    # PostBody - стиль для текста (12pt)
    post_body_style = ET.SubElement(parent, 'CharacterStyle',
                                    Self='CharacterStyle/PostBody',
                                    Name='PostBody')
    props = ET.SubElement(post_body_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = FONTS['body']
    ET.SubElement(props, 'PointSize', type='double').text = '12'
    ET.SubElement(props, 'FillColor', type='string').text = 'Color/Black'


def _create_paragraph_styles(parent):
    """Создает Paragraph Styles"""
    
    # Default [No paragraph style]
    ET.SubElement(parent, 'ParagraphStyle',
                  Self='ParagraphStyle/$ID/[No paragraph style]',
                  Name='$ID/[No paragraph style]')
    
    # PostDate - дата поста
    ET.SubElement(parent, 'ParagraphStyle',
                  Self='ParagraphStyle/PostDate',
                  Name='PostDate',
                  SpaceAfter='4',
                  Justification='RightAlign')
    
    # PostBody - основной текст
    ET.SubElement(parent, 'ParagraphStyle',
                  Self='ParagraphStyle/PostBody',
                  Name='PostBody',
                  SpaceAfter='12',
                  Justification='LeftAlign')


def _create_object_styles(parent):
    """Создает Object Styles для frames"""
    
    # Default
    ET.SubElement(parent, 'ObjectStyle',
                  Self='ObjectStyle/$ID/[None]',
                  Name='$ID/[None]')
    
    # MediaFrame - для изображений
    media_style = ET.SubElement(parent, 'ObjectStyle',
                                Self='ObjectStyle/MediaFrame',
                                Name='MediaFrame')
    props = ET.SubElement(media_style, 'Properties')
    ET.SubElement(props, 'StrokeWeight', type='double').text = '0'
    
    # GalleryFrame - для галерей
    gallery_style = ET.SubElement(parent, 'ObjectStyle',
                                   Self='ObjectStyle/GalleryFrame',
                                   Name='GalleryFrame')
    props = ET.SubElement(gallery_style, 'Properties')
    ET.SubElement(props, 'StrokeWeight', type='double').text = '0'
