"""
Генерация дополнительных ресурсов для IDML
"""

from lxml import etree as ET


def generate_graphic_xml():
    """Генерирует пустой Graphic.xml"""
    root = ET.Element('GraphicList', nsmap={
        None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
    })
    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def generate_fonts_xml():
    """Генерирует Fonts.xml с используемыми шрифтами"""
    root = ET.Element('FontList', nsmap={
        None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
    })
    
    # Arial
    arial = ET.SubElement(root, 'FontFamily', Self='di2i3', Name='Arial')
    ET.SubElement(arial, 'Font', Self='di2i4', FontFamily='Arial', Name='Regular',
                  PostScriptName='ArialMT', FontStyleName='Regular')
    ET.SubElement(arial, 'Font', Self='di2i5', FontFamily='Arial', Name='Bold',
                  PostScriptName='Arial-BoldMT', FontStyleName='Bold')
    ET.SubElement(arial, 'Font', Self='di2i6', FontFamily='Arial', Name='Italic',
                  PostScriptName='Arial-ItalicMT', FontStyleName='Italic')
    
    # Courier New (для кода)
    courier = ET.SubElement(root, 'FontFamily', Self='di2i7', Name='Courier New')
    ET.SubElement(courier, 'Font', Self='di2i8', FontFamily='Courier New', Name='Regular',
                  PostScriptName='CourierNewPSMT', FontStyleName='Regular')
    
    # Segoe UI Emoji (для эмодзи)
    emoji = ET.SubElement(root, 'FontFamily', Self='di2i9', Name='Segoe UI Emoji')
    ET.SubElement(emoji, 'Font', Self='di2i10', FontFamily='Segoe UI Emoji', Name='Regular',
                  PostScriptName='SegoeUIEmoji', FontStyleName='Regular')
    
    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def generate_preferences_xml():
    """Генерирует Preferences.xml с базовыми настройками"""
    nsmap = {
        'idPkg': 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging',
        None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
    }
    idPkg_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
    
    root = ET.Element(f'{idPkg_ns}Preferences', nsmap=nsmap)
    
    # Properties wrapper
    props = ET.SubElement(root, 'Properties')
    
    # Базовые настройки документа
    ET.SubElement(props, 'TextDefault',
                  HorizontalMeasurementUnits='Points',
                  VerticalMeasurementUnits='Points',
                  TextSize='10',
                  AppliedFont='Arial')
    
    ET.SubElement(props, 'DocumentPreference',
                  PageWidth='595.28',
                  PageHeight='841.89',
                  PageOrientation='Portrait',
                  PagesPerDocument='1')
    
    ET.SubElement(props, 'GridPreference',
                  HorizontalGridlineDivision='12',
                  VerticalGridlineDivision='12')
    
    ET.SubElement(props, 'GuidePreference',
                  GuidesInBack='true',
                  GuidesLocked='false',
                  GuidesShown='true')
    
    ET.SubElement(props, 'MarginPreference',
                  Top='56.69',
                  Bottom='56.69',
                  Left='56.69',
                  Right='56.69',
                  ColumnCount='1',
                  ColumnGutter='14.17')
    
    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
