# 🔧 Исправление прогрессбара загрузки канала

## Проблема:
После рефакторинга API endpoints пропал прогрессбар загрузки канала.

## Причина:
Во время разделения endpoints по модулям был потерян endpoint `/api/download/progress/<channel_id>` для обновления прогресса.

## Решение:

### ✅ Восстановлен endpoint в `api/downloads.py`:
```python
@downloads_bp.route('/download/progress/<channel_id>', methods=['POST'])
def update_progress(channel_id):
    """Обновляет прогресс загрузки канала"""
    try:
        _, _, _, _, update_download_progress = get_download_globals()
        
        data = request.get_json()
        posts_processed = data.get('posts_processed', 0)
        total_posts = data.get('total_posts', 0)
        comments_processed = data.get('comments_processed', 0)
        
        update_download_progress(channel_id, posts_processed, total_posts, comments_processed)
        return jsonify({'message': 'Прогресс обновлен'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### ✅ Обновлена функция `get_download_globals()`:
- Добавлен импорт `app.update_download_progress`
- Все функции исправлены для работы с 5 параметрами

### ✅ Проверена интеграция:
- `telegram_export.py` уже содержит функцию `update_import_progress()` которая правильно обращается к API
- Фронтенд (`DownloadStatus.vue`) готов для отображения прогресса
- Все endpoints для управления загрузкой работают

## Результат:
Прогрессбар загрузки канала снова функционирует! 📊

Теперь во время загрузки канала:
1. Backend обновляет прогресс через `update_import_progress()`
2. API endpoint `/api/download/progress/<channel_id>` принимает обновления
3. Фронтенд отображает актуальный прогресс в реальном времени
