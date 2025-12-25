"""
Генерация Styles.xml для IDML документа
Содержит Paragraph Styles, Character Styles, Object Styles
"""

from lxml import etree as ET
from .constants import FONTS, PARAGRAPH_STYLES, ENTITY_TO_CHAR_STYLE


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
    """Создает Character Styles для Telegram форматирования"""
    
    # Default [No character style]
    ET.SubElement(parent, 'CharacterStyle',
                  Self='CharacterStyle/$ID/[No character style]',
                  Name='$ID/[No character style]')
    
    # Bold
    bold_style = ET.SubElement(parent, 'CharacterStyle',
                               Self='CharacterStyle/TelegramBold',
                               Name='TelegramBold')
    ET.SubElement(bold_style, 'Properties')
    props = ET.SubElement(bold_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = FONTS['body']
    ET.SubElement(props, 'FontStyle', type='string').text = 'Bold'
    
    # Italic
    italic_style = ET.SubElement(parent, 'CharacterStyle',
                                 Self='CharacterStyle/TelegramItalic',
                                 Name='TelegramItalic')
    props = ET.SubElement(italic_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = FONTS['body']
    ET.SubElement(props, 'FontStyle', type='string').text = 'Italic'
    
    # Code (monospace)
    code_style = ET.SubElement(parent, 'CharacterStyle',
                               Self='CharacterStyle/TelegramCode',
                               Name='TelegramCode')
    props = ET.SubElement(code_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = FONTS['code']
    ET.SubElement(props, 'PointSize', type='double').text = str(FONTS['code_size'])
    
    # Link (blue + underline)
    link_style = ET.SubElement(parent, 'CharacterStyle',
                               Self='CharacterStyle/TelegramLink',
                               Name='TelegramLink')
    props = ET.SubElement(link_style, 'Properties')
    ET.SubElement(props, 'FillColor', type='string').text = 'Color/Blue'
    ET.SubElement(props, 'Underline', type='boolean').text = 'true'
    
    # Mention
    mention_style = ET.SubElement(parent, 'CharacterStyle',
                                  Self='CharacterStyle/TelegramMention',
                                  Name='TelegramMention')
    props = ET.SubElement(mention_style, 'Properties')
    ET.SubElement(props, 'FillColor', type='string').text = 'Color/Blue'
    
    # Strikethrough
    strike_style = ET.SubElement(parent, 'CharacterStyle',
                                 Self='CharacterStyle/TelegramStrike',
                                 Name='TelegramStrike')
    props = ET.SubElement(strike_style, 'Properties')
    ET.SubElement(props, 'StrikeThru', type='boolean').text = 'true'
    
    # Underline
    underline_style = ET.SubElement(parent, 'CharacterStyle',
                                    Self='CharacterStyle/TelegramUnderline',
                                    Name='TelegramUnderline')
    props = ET.SubElement(underline_style, 'Properties')
    ET.SubElement(props, 'Underline', type='boolean').text = 'true'


def _create_paragraph_styles(parent):
    """Создает Paragraph Styles"""
    
    # Default [No paragraph style]
    ET.SubElement(parent, 'ParagraphStyle',
                  Self='ParagraphStyle/$ID/[No paragraph style]',
                  Name='$ID/[No paragraph style]')
    
    # PostHeader - автор и дата
    header_style = ET.SubElement(parent, 'ParagraphStyle',
                                  Self='ParagraphStyle/PostHeader',
                                  Name='PostHeader')
    props = ET.SubElement(header_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = PARAGRAPH_STYLES['PostHeader']['font']
    ET.SubElement(props, 'PointSize', type='double').text = str(PARAGRAPH_STYLES['PostHeader']['size'])
    ET.SubElement(props, 'FillColor', type='string').text = PARAGRAPH_STYLES['PostHeader']['color']
    ET.SubElement(props, 'SpaceAfter', type='double').text = str(PARAGRAPH_STYLES['PostHeader']['space_after'])
    
    # PostBody - основной текст
    body_style = ET.SubElement(parent, 'ParagraphStyle',
                               Self='ParagraphStyle/PostBody',
                               Name='PostBody')
    props = ET.SubElement(body_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = PARAGRAPH_STYLES['PostBody']['font']
    ET.SubElement(props, 'PointSize', type='double').text = str(PARAGRAPH_STYLES['PostBody']['size'])
    ET.SubElement(props, 'SpaceAfter', type='double').text = str(PARAGRAPH_STYLES['PostBody']['space_after'])
    ET.SubElement(props, 'Justification', type='enumeration').text = 'LeftAlign'
    
    # PostQuote - цитата
    quote_style = ET.SubElement(parent, 'ParagraphStyle',
                                Self='ParagraphStyle/PostQuote',
                                Name='PostQuote')
    props = ET.SubElement(quote_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = PARAGRAPH_STYLES['PostQuote']['font']
    ET.SubElement(props, 'PointSize', type='double').text = str(PARAGRAPH_STYLES['PostQuote']['size'])
    ET.SubElement(props, 'FillColor', type='string').text = PARAGRAPH_STYLES['PostQuote']['color']
    ET.SubElement(props, 'LeftIndent', type='double').text = str(PARAGRAPH_STYLES['PostQuote']['left_indent'])
    ET.SubElement(props, 'SpaceAfter', type='double').text = str(PARAGRAPH_STYLES['PostQuote']['space_after'])
    
    # PostFooter - реакции и views
    footer_style = ET.SubElement(parent, 'ParagraphStyle',
                                  Self='ParagraphStyle/PostFooter',
                                  Name='PostFooter')
    props = ET.SubElement(footer_style, 'Properties')
    ET.SubElement(props, 'AppliedFont', type='string').text = PARAGRAPH_STYLES['PostFooter']['font']
    ET.SubElement(props, 'PointSize', type='double').text = str(PARAGRAPH_STYLES['PostFooter']['size'])
    ET.SubElement(props, 'FillColor', type='string').text = PARAGRAPH_STYLES['PostFooter']['color']
    ET.SubElement(props, 'SpaceAfter', type='double').text = str(PARAGRAPH_STYLES['PostFooter']['space_after'])


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
