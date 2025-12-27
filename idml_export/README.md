# IDML Export Module

Модуль для экспорта Telegram каналов в формат InDesign (IDML) с поддержкой текста и медиа.

## Возможности

✅ Экспорт текстовых постов  
✅ Экспорт изображений с автоматическим масштабированием  
✅ Поддержка разных размеров страниц (A4, US Letter)  
✅ Настройка полей и колонок  
✅ Автоматическая упаковка медиа-файлов в IDML пакет  
✅ Сохранение пропорций изображений  

## Структура

```
idml_export/
├── __init__.py          # Экспорт IDMLBuilder
├── builder.py           # Основной класс для создания IDML
├── constants.py         # Константы (размеры страниц, шрифты, стили)
├── coordinates.py       # Утилиты для работы с координатами
├── styles.py            # Генерация Styles.xml
├── resources.py         # Генерация Resources (Fonts, Graphic, Preferences)
└── templates/           # (зарезервировано для будущих XML шаблонов)
```

## Использование

### Базовый пример

```python
from idml_export.builder import IDMLBuilder
from models import Channel, Post

# Получаем канал и настройки
channel = Channel.query.get('channel_id')
print_settings = channel.print_settings or {}

# Создаем builder
builder = IDMLBuilder(channel, print_settings)
builder.create_document()

# Добавляем текстовый контент
story_id = builder.add_text_story("Hello from Telegram!", 'PostBody')
builder.add_text_frame(story_id, bounds=[100, 100, 200, 400])

# Сохраняем
builder.save('output.idml')
```

### Добавление поста с медиа (новое!)

```python
# Получаем посты
posts = Post.query.filter_by(channel_id=channel.id).all()

# Добавляем каждый пост (текст + медиа)
for post in posts:
    builder.add_post(post, downloads_dir='downloads')

# Сохраняем - медиа-файлы автоматически упакуются в Links/
builder.save('output_with_media.idml')
```

### Через API

```bash
GET /api/channels/{channel_id}/export-idml
```

## Настройки печати

### Глобальные (в Channel.print_settings)

```json
{
  "page_size": "A4",
  "margins": [56.69, 56.69, 56.69, 56.69],
  "text_columns": 1,
  "column_gutter": 14.17,
  "master_page_enabled": true,
  "include_headers_footers": true
}
```

### Индивидуальные для поста (в Post.print_settings)

```json
{
  "text_columns": 2,
  "image_placement": "above_text",
  "page_break_before": false,
  "keep_with_next": false
}
```

## Стили

### Paragraph Styles
- `PostHeader` — автор и дата
- `PostBody` — основной текст
- `PostQuote` — цитаты
- `PostFooter` — реакции и views

### Character Styles
- `TelegramBold` — жирный текст
- `TelegramItalic` — курсив
- `TelegramCode` — моноширинный код
- `TelegramLink` — ссылки
- `TelegramMention` — упоминания
- `TelegramStrike` — зачеркнутый
- `TelegramUnderline` — подчеркнутый

## Координатная система InDesign

- **GeometricBounds**: `[y1, x1, y2, x2]` (Y идет первым!)
- **Единицы**: points (1pt = 1/72 inch = 0.3528 mm)
- **Начало координат**: левый верхний угол страницы

### Размеры страниц

- **A4**: 595.28 × 841.89 points (210 × 297 mm)
- **US Letter**: 612 × 792 points (8.5 × 11 inch)

## Графика в IDML

### Links (рекомендуется)
Изображения лежат отдельно, в IDML только ссылки:

```xml
<Rectangle>
  <Image>
    <Link LinkResourceURI="file:///path/to/image.jpg"/>
  </Image>
</Rectangle>
```

### Embedded
Изображения встраиваются в Base64 (увеличивает размер файла).

## Следующие шаги

### TODO
- [ ] Парсинг Telegram markdown entities → Character Styles
- [ ] Конверсия gallery layout JSON → IDML frames
- [ ] Master Pages с header/footer
- [ ] Threaded text frames (связанные текстовые фреймы)
- [ ] Поддержка колонок текста
- [ ] Emoji как inline graphics или unicode
- [ ] Polls форматирование
- [ ] Video placeholders

## Тестирование

1. Скачайте канал
2. Нажмите кнопку "IDML" в UI
3. Скачайте файл `downloads/{channel_id}/{channel_id}.idml`
4. Откройте в Adobe InDesign
5. Проверьте:
   - Открывается ли файл без ошибок
   - Видны ли тексты
   - Применены ли стили

## Полезные ссылки

- [IDML Specification](https://www.adobe.com/devnet/indesign/documentation.html)
- [InDesign CS6 Scripting Guide](https://www.adobe.com/devnet/indesign/sdk.html)
