"""
Тестовый скрипт для проверки экспорта IDML с медиа
"""

from idml_export.builder import IDMLBuilder
from models import Channel, Post, db
from app import app
import os

def test_idml_export_with_media():
    """Тестирует экспорт IDML документа с медиа"""
    
    with app.app_context():
        # Получаем первый канал с постами
        channel = Channel.query.first()
        
        if not channel:
            print("❌ Каналы не найдены в базе данных")
            return
        
        print(f"✓ Найден канал: {channel.name} ({channel.id})")
        
        # Получаем посты с медиа
        posts = Post.query.filter_by(channel_id=channel.id).filter(
            Post.media_url.isnot(None)
        ).limit(5).all()
        
        if not posts:
            print("❌ Посты с медиа не найдены")
            # Попробуем любые посты
            posts = Post.query.filter_by(channel_id=channel.id).limit(5).all()
            if not posts:
                print("❌ Посты вообще не найдены")
                return
            print(f"ℹ Используем {len(posts)} постов без медиа")
        else:
            print(f"✓ Найдено {len(posts)} постов с медиа")
        
        # Создаем builder
        print_settings = channel.print_settings or {}
        builder = IDMLBuilder(channel, print_settings)
        builder.create_document()
        
        print("✓ Документ создан")
        
        # Добавляем посты
        downloads_dir = 'downloads'
        
        for i, post in enumerate(posts, 1):
            print(f"  Добавляю пост {i}/{len(posts)}: {post.telegram_id}")
            
            if post.media_url:
                media_path = os.path.join(downloads_dir, post.media_url)
                if os.path.exists(media_path):
                    print(f"    ✓ Медиа найдено: {post.media_url}")
                else:
                    print(f"    ⚠ Медиа не найдено: {media_path}")
            
            builder.add_post(post, downloads_dir)
        
        print(f"✓ Все {len(posts)} постов добавлены")
        print(f"  - Stories: {len(builder.stories)}")
        print(f"  - Frames: {len(builder.current_page['frames'])}")
        print(f"  - Media files: {len(builder.media_files)}")
        
        # Сохраняем
        output_path = f'/tmp/test_media_{channel.id}.idml'
        builder.save(output_path)
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / 1024  # KB
            print(f"\n✅ IDML файл успешно создан!")
            print(f"   Путь: {output_path}")
            print(f"   Размер: {size:.1f} KB")
            
            # Проверяем содержимое
            import zipfile
            with zipfile.ZipFile(output_path, 'r') as z:
                files = z.namelist()
                print(f"   Файлов в архиве: {len(files)}")
                
                links = [f for f in files if f.startswith('Links/')]
                if links:
                    print(f"   Медиа файлов: {len(links)}")
                    for link in links[:3]:  # Показываем первые 3
                        print(f"     - {link}")
                else:
                    print("   ⚠ Медиа файлы не найдены в архиве")
        else:
            print(f"\n❌ Файл не был создан")

if __name__ == '__main__':
    test_idml_export_with_media()
