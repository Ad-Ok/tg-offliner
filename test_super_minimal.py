"""
Создает супер-минимальный IDML с пустой страницей без фреймов
"""
import zipfile
import os
from lxml import etree as ET

def create_super_minimal():
    output = '/tmp/super_minimal.idml'
    temp_dir = '/tmp/super_minimal_temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    # mimetype
    with open(os.path.join(temp_dir, 'mimetype'), 'w') as f:
        f.write('application/vnd.adobe.indesign-idml-package')
    
    # META-INF/container.xml
    os.makedirs(os.path.join(temp_dir, 'META-INF'), exist_ok=True)
    container_ns = 'urn:oasis:names:tc:opendocument:xmlns:container'
    container = ET.Element('container', version='1.0', xmlns=container_ns)
    rootfiles = ET.SubElement(container, 'rootfiles')
    ET.SubElement(rootfiles, 'rootfile', {'full-path': 'designmap.xml', 'media-type': 'text/xml'})
    tree = ET.ElementTree(container)
    ET.indent(tree, space='  ')
    tree.write(os.path.join(temp_dir, 'META-INF', 'container.xml'),
               encoding='UTF-8', xml_declaration=True, standalone='yes')
    
    # XML/BackingStory.xml
    os.makedirs(os.path.join(temp_dir, 'XML'), exist_ok=True)
    idPkg_ns = '{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}'
    backing = ET.Element(f'{idPkg_ns}BackingStory', DOMVersion='17.0')
    xml_story = ET.SubElement(backing, 'XmlStory', Self='ub0', UserText='true',
                              IsEndnoteStory='false', AppliedTOCStyle='n',
                              TrackChanges='false', StoryTitle='$ID/',
                              AppliedNamedGrid='n')
    para_range = ET.SubElement(xml_story, 'ParagraphStyleRange',
                              AppliedParagraphStyle='ParagraphStyle/$ID/NormalParagraphStyle')
    char_range = ET.SubElement(para_range, 'CharacterStyleRange',
                              AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
    ET.SubElement(char_range, 'XMLElement', Self='di2', MarkupTag='XMLTag/Root')
    content = ET.SubElement(char_range, 'Content')
    content.text = ''
    tree = ET.ElementTree(backing)
    ET.indent(tree, space='  ')
    tree.write(os.path.join(temp_dir, 'XML', 'BackingStory.xml'),
               encoding='UTF-8', xml_declaration=True, standalone='yes')
    
    # XML/Tags.xml
    tags = ET.Element(f'{idPkg_ns}Tags', DOMVersion='17.0')
    xml_tag = ET.SubElement(tags, 'XMLTag', Self='XMLTag/Root', Name='Root')
    props = ET.SubElement(xml_tag, 'Properties')
    color = ET.SubElement(props, 'TagColor', type='enumeration')
    color.text = 'LightBlue'
    tree = ET.ElementTree(tags)
    ET.indent(tree, space='  ')
    tree.write(os.path.join(temp_dir, 'XML', 'Tags.xml'),
               encoding='UTF-8', xml_declaration=True, standalone='yes')
    
    # Resources/Graphic.xml
    os.makedirs(os.path.join(temp_dir, 'Resources'), exist_ok=True)
    graphic = ET.Element('GraphicList',
                        nsmap={None: 'http://ns.adobe.com/AdobeInDesign/4.0/'})
    tree = ET.ElementTree(graphic)
    tree.write(os.path.join(temp_dir, 'Resources', 'Graphic.xml'),
               encoding='UTF-8', xml_declaration=True)
    
    # Spreads/Spread_u1.xml - ПУСТОЙ Spread
    os.makedirs(os.path.join(temp_dir, 'Spreads'), exist_ok=True)
    idPkg_ns_str = 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging'
    spread_root = ET.Element(f'{idPkg_ns}Spread',
                             nsmap={'idPkg': idPkg_ns_str}, DOMVersion='17.0')
    
    spread = ET.SubElement(spread_root, 'Spread',
                          Self='u1',
                          PageTransitionType='None',
                          ShowMasterItems='true',
                          PageCount='1',
                          BindingLocation='0',
                          ItemTransform='1 0 0 1 0 0',
                          FlattenerOverride='Default')
    
    ET.SubElement(spread, 'FlattenerPreference')
    
    page = ET.SubElement(spread, 'Page',
                        Self='u2',
                        GeometricBounds='0 0 841.89 595.28',
                        ItemTransform='1 0 0 1 0 0')
    
    tree = ET.ElementTree(spread_root)
    ET.indent(tree, space='  ')
    tree.write(os.path.join(temp_dir, 'Spreads', 'Spread_u1.xml'),
               encoding='UTF-8', xml_declaration=True, standalone='yes')
    
    # designmap.xml
    idPkg_ns_str = 'http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging'
    nsmap = {'idPkg': idPkg_ns_str}
    doc = ET.Element('Document', nsmap=nsmap)
    doc.set('DOMVersion', '17.0')
    doc.set('Self', 'd')
    doc.set('StoryList', 'ub0')
    doc.set('Name', 'super_minimal.idml')
    doc.set('ZeroPoint', '0 0')
    doc.set('ActiveLayer', 'u3')
    
    lang = ET.SubElement(doc, 'Language',
                        Self='Language/$ID/English%3a USA',
                        Name='$ID/English: USA',
                        SingleQuotes="''",
                        DoubleQuotes='""',
                        PrimaryLanguageName='$ID/English',
                        SublanguageName='$ID/USA',
                        Id='269',
                        HyphenationVendor='Hunspell',
                        SpellingVendor='Hunspell')
    
    ET.SubElement(doc, f'{idPkg_ns}Graphic', src='Resources/Graphic.xml')
    ET.SubElement(doc, f'{idPkg_ns}Tags', src='XML/Tags.xml')
    
    layer = ET.SubElement(doc, 'Layer',
                         Self='u3',
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
    
    ET.SubElement(doc, f'{idPkg_ns}Spread', src='Spreads/Spread_u1.xml')
    ET.SubElement(doc, f'{idPkg_ns}BackingStory', src='XML/BackingStory.xml')
    
    tree = ET.ElementTree(doc)
    xml_str = ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    aid_directive = b'<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="17.4(51)" ?>\n'
    lines = xml_str.split(b'\n', 1)
    
    with open(os.path.join(temp_dir, 'designmap.xml'), 'wb') as f:
        f.write(lines[0] + b'\n' + aid_directive + lines[1])
    
    # Создаем ZIP
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(temp_dir, 'mimetype'), 'mimetype',
                compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                z.write(file_path, arcname)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    size = os.path.getsize(output)
    print(f"✅ Создан super minimal IDML: {output}")
    print(f"📦 Размер: {size} байт")

if __name__ == '__main__':
    create_super_minimal()
