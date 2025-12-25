"""
Создает минимальный рабочий IDML для InDesign 2022
Основано на спецификации InDesign CS6+
"""

import zipfile
from lxml import etree as ET

def create_minimal_idml(output_path='/tmp/minimal_working.idml'):
    """Создает минимальный валидный IDML файл"""
    
    # 1. mimetype (без сжатия!)
    mimetype = b'application/vnd.adobe.indesign-idml-package'
    
    # 2. designmap.xml
    designmap = ET.Element('Document', {
        'DOMVersion': '17.0'
    }, nsmap={'idPkg': 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging'})
    
    idPkg = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
    ET.SubElement(designmap, f'{idPkg}Spread', src='Spreads/Spread_u6.xml')
    ET.SubElement(designmap, f'{idPkg}Story', src='Stories/Story_u18i.xml')
    ET.SubElement(designmap, 'Styles', src='Resources/Styles.xml')
    
    # 3. Spread
    spread = ET.Element('Spread', {
        'Self': 'u6',
        'FlattenerOverride': 'Default'
    }, nsmap={None: 'http://ns.adobe.com/AdobeInDesign/4.0/'})
    
    ET.SubElement(spread, 'FlattenerPreference')
    
    page = ET.SubElement(spread, 'Page', {
        'Self': 'u7',
        'GeometricBounds': '0 0 841.89 595.28',
        'ItemTransform': '1 0 0 1 0 0'
    })
    
    # TextFrame с минимальными требованиями
    text_frame = ET.SubElement(page, 'TextFrame', {
        'Self': 'u8',
        'ParentStory': 'u18i',
        'GeometricBounds': '56.69 56.69 785.2 538.59',
        'ItemTransform': '1 0 0 1 0 0',
        'ContentType': 'TextType'
    })
    
    props = ET.SubElement(text_frame, 'Properties')
    path_geo = ET.SubElement(props, 'PathGeometry')
    geo_path = ET.SubElement(path_geo, 'GeometryPathType', PathOpen='false')
    path_points = ET.SubElement(geo_path, 'PathPointArray')
    
    # Минимум 4 точки для прямоугольника
    for anchor, left, right in [
        ('56.69 56.69', '56.69 56.69', '56.69 56.69'),
        ('56.69 538.59', '56.69 538.59', '56.69 538.59'),
        ('785.2 538.59', '785.2 538.59', '785.2 538.59'),
        ('785.2 56.69', '785.2 56.69', '785.2 56.69'),
    ]:
        ET.SubElement(path_points, 'PathPointType', {
            'Anchor': anchor,
            'LeftDirection': left,
            'RightDirection': right
        })
    
    # 4. Story
    story = ET.Element('Story', {
        'Self': 'u18i',
        'AppliedTOCStyle': 'n',
        'TrackChanges': 'false'
    }, nsmap={None: 'http://ns.adobe.com/AdobeInDesign/4.0/'})
    
    ET.SubElement(story, 'StoryPreference', {
        'OpticalMarginAlignment': 'false',
        'OpticalMarginSize': '12'
    })
    
    para_range = ET.SubElement(story, 'ParagraphStyleRange', {
        'AppliedParagraphStyle': 'ParagraphStyle/$ID/NormalParagraphStyle'
    })
    
    char_range = ET.SubElement(para_range, 'CharacterStyleRange', {
        'AppliedCharacterStyle': 'CharacterStyle/$ID/[No character style]'
    })
    
    content = ET.SubElement(char_range, 'Content')
    content.text = 'Hello from Telegram!\nThis is a test IDML document for InDesign 2022.'
    
    # 5. Styles.xml (минимальный)
    styles_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
    styles = ET.Element(f'{styles_ns}Styles', nsmap={
        'idPkg': 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging',
        None: 'http://ns.adobe.com/AdobeInDesign/4.0/'
    })
    
    # RootCharacterStyleGroup
    char_group = ET.SubElement(styles, 'RootCharacterStyleGroup', Self='character-style-group-root')
    ET.SubElement(char_group, 'CharacterStyle', {
        'Self': 'CharacterStyle/$ID/[No character style]',
        'Name': '$ID/[No character style]'
    })
    
    # RootParagraphStyleGroup
    para_group = ET.SubElement(styles, 'RootParagraphStyleGroup', Self='paragraph-style-group-root')
    ET.SubElement(para_group, 'ParagraphStyle', {
        'Self': 'ParagraphStyle/$ID/NormalParagraphStyle',
        'Name': '$ID/NormalParagraphStyle'
    })
    
    # Создаем ZIP архив
    with zipfile.ZipFile(output_path, 'w') as z:
        # mimetype без компрессии
        z.writestr('mimetype', mimetype, compress_type=zipfile.ZIP_STORED)
        
        # XML files с компрессией
        z.writestr('designmap.xml', ET.tostring(designmap, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
        z.writestr('Spreads/Spread_u6.xml', ET.tostring(spread, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
        z.writestr('Stories/Story_u18i.xml', ET.tostring(story, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
        z.writestr('Resources/Styles.xml', ET.tostring(styles, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
    
    print(f"✅ Создан минимальный IDML: {output_path}")
    print(f"📦 Размер: {open(output_path, 'rb').seek(0, 2)} байт")
    
    return output_path

if __name__ == '__main__':
    create_minimal_idml()
