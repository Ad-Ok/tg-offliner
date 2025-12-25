#!/usr/bin/env python
"""
Тестовый скрипт для проверки IDML генерации
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from idml_export.builder import IDMLBuilder
from models import Channel


def test_minimal_idml():
    """Создает минимальный тестовый IDML документ"""
    print("=== Тест минимального IDML документа ===\n")
    
    # Создаем фейковый канал
    class FakeChannel:
        id = 'test_channel'
        name = 'Test Channel'
        print_settings = None
    
    channel = FakeChannel()
    
    print("1. Создание IDMLBuilder...")
    builder = IDMLBuilder(channel)
    
    print("2. Создание документа...")
    builder.create_document()
    
    print("3. Добавление текстового контента...")
    story_id = builder.add_text_story("Hello from Telegram!\n\nThis is a test IDML export.", 'PostBody')
    
    # Простой текстовый фрейм
    bounds = [100, 100, 200, 400]
    builder.add_text_frame(story_id, bounds)
    
    print("4. Добавление второго поста...")
    story_id2 = builder.add_text_story("Second post with some text.", 'PostBody')
    bounds2 = [220, 100, 300, 400]
    builder.add_text_frame(story_id2, bounds2)
    
    print("5. Сохранение IDML...")
    output_path = '/tmp/test_minimal.idml'
    builder.save(output_path)
    
    print(f"\n✅ Успешно создан: {output_path}")
    print(f"📦 Размер файла: {os.path.getsize(output_path)} байт")
    
    # Проверяем структуру
    import zipfile
    with zipfile.ZipFile(output_path, 'r') as z:
        print(f"\n📋 Содержимое IDML:")
        for name in sorted(z.namelist()):
            info = z.getinfo(name)
            print(f"  - {name} ({info.file_size} байт)")
    
    print(f"\n💡 Откройте файл в Adobe InDesign: {output_path}")
    return output_path


if __name__ == '__main__':
    try:
        test_minimal_idml()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
