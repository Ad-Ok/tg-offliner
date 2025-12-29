# Freeze Layout Feature - Спецификация

**Дата:** 28 декабря 2025  
**Версия:** 1.0  
**Статус:** В разработке

## 🎯 Цели

### Конечная цель
Получить **IDML**, в точности соответствующий preview

### Промежуточная цель  
Получить **PDF**, полностью соответствующий preview

### Предварительная цель
Получить правильно разбитый на **страницы preview**

---

## 📋 Требования

### Функциональные

1. **Пагинация контента:**
   - Разбиение ленты на страницы с учетом `print-config.json`
   - **Каждый пост и комментарий - независимая единица пагинации**
   - Комментарии имеют визуальное оформление (отступ слева), но разбиваются отдельно
   - Поддержка длинных постов (не помещаются на одну страницу)
   - Обработка галерей и группировок

2. **Freeze Layout:**
   - Преобразование flow layout в absolute positioning
   - Координаты в миллиметрах (из print-config)
   - Сохранение в БД (таблица `pages`)

3. **Пагинация UI:**
   - Lazy loading страниц (по 20 штук)
   - Кнопка "Загрузить еще"
   - Индикатор прогресса

4. **Экспорт:**
   - PDF с точными координатами из frozen layout
   - IDML с точными координатами из frozen layout

### Технические

1. **Performance:**
   - Обработка до 20 страниц за раз
   - Виртуализация для больших каналов
   - Кеширование frozen layouts

2. **БД:**
   - Таблица `pages` для хранения frozen layouts
   - Иерархия: `page_number` → `posts[]` → `elements[]`
   - Каждый пост содержит координаты + вложенные элементы (текст, изображения, галереи)

3. **Координаты:**
   - Единицы: миллиметры (из print-config.json)
   - Относительно верхнего левого угла страницы
   - С учетом margins из `Channel.print_settings`

---

## 🏗️ Архитектура

### 1. Разбиение на страницы

```mermaid
graph TD
    A[Posts Array] --> B{Has Comments?}
    B -->|Yes| C[Group: Post + Comments]
    B -->|No| D[Single Post]
    C --> E[Check Page Height]
    D --> E
    E -->|Fits| F[Add to Current Page]
    E -->|Overflow| G[Start New Page]
    G --> H[Mark with page-break-before]
    F --> I[Continue]
```

#### Алгоритм разбиения

```javascript
function paginateContent(posts, pageConfig) {
  const pages = [];
  let currentPage = createNewPage(1, pageConfig);
  
  // Плоский массив: главные посты + комментарии как отдельные единицы
  const flatItems = [];
  
  posts.forEach(post => {
    // Добавляем главный пост
    flatItems.push({
      type: 'post',
      data: post,
      isComment: false,
      element: null
    });
    
    // Добавляем каждый комментарий как отдельную единицу
    if (post.comments && post.comments.length > 0) {
      post.comments.forEach(comment => {
        flatItems.push({
          type: 'comment',
          data: comment,
          isComment: true,
          parentPostId: post.telegram_id,
          element: null
        });
      });
    }
  });
  
  // Обрабатываем каждый элемент независимо
  flatItems.forEach(item => {
    // 1. Рендерим во временный container для измерения
    const tempContainer = renderToTempContainer(item);
    item.height = tempContainer.offsetHeight;
    item.element = tempContainer;
    
    // 2. Проверяем, поместится ли на текущей странице
    if (currentPage.height + item.height > currentPage.maxHeight) {
      // Не помещается - начинаем новую страницу
      
      // ВАЖНО: Если элемент слишком большой для одной страницы,
      // помечаем его для особой обработки (может потребоваться разбиение)
      if (item.height > currentPage.maxHeight) {
        console.warn(`Элемент ${item.type} ${item.data.telegram_id} слишком большой (${item.height}px > ${currentPage.maxHeight}px)`);
        // TODO: В будущем можно разбить контент на части
      }
      
      pages.push(currentPage);
      currentPage = createNewPage(pages.length + 1, pageConfig);
      item.pageBreakBefore = true;
    }
    
    // Добавляем элемент на текущую страницу
    currentPage.items.push(item);
    currentPage.height += item.height;
  });
  
  // Добавляем последнюю страницу
  if (currentPage.items.length > 0) {
    pages.push(currentPage);
  }
  
  return pages;
}

function createNewPage(number, pageConfig) {
  return {
    number: number,
    items: [],
    height: 0,
    maxHeight: pageConfig.height - pageConfig.margins.top - pageConfig.margins.bottom
  };
}
```

#### Обработка постов и комментариев

**Ключевой принцип:** Каждый пост и комментарий - независимая единица для пагинации

**HTML структура:**
```html
<div class="mb-6">
  <!-- Главный пост -->
  <div class="post-container" data-post-id="2344">
    <div class="post"><!-- Контент поста --></div>
    <div class="post-footer"><!-- Реакции --></div>
  </div>
  
  <!-- Комментарии (каждый - отдельный элемент) -->
  <div class="ml-8 mt-4">
    <div class="post-container" data-post-id="5286" data-is-comment="true">
      <div class="post"><!-- Контент комментария --></div>
    </div>
    <div class="post-container" data-post-id="5287" data-is-comment="true">
      <div class="post"><!-- Контент комментария --></div>
    </div>
  </div>
</div>
```

**Алгоритм обработки:**
```javascript
function flattenPostsAndComments(container) {
  const flatItems = [];
  
  // Находим все главные посты и группы
  const mainBlocks = container.querySelectorAll('.mb-6');
  
  mainBlocks.forEach(block => {
    // 1. Главный пост
    const mainPost = block.querySelector('.post-container:not([data-is-comment])');
    if (mainPost) {
      flatItems.push({
        type: 'post',
        element: mainPost,
        telegram_id: mainPost.dataset.postId,
        isComment: false,
        indent: 0
      });
    }
    
    // 2. Комментарии как отдельные элементы
    const comments = block.querySelectorAll('.post-container[data-is-comment="true"]');
    comments.forEach(comment => {
      flatItems.push({
        type: 'comment',
        element: comment,
        telegram_id: comment.dataset.postId,
        isComment: true,
        parentPostId: mainPost?.dataset.postId,
        indent: 32 // ml-8 = 32px = ~8.47mm
      });
    });
  });
  
  return flatItems;
}
```

**Особенности:**
- Комментарии сохраняют отступ слева (`ml-8` = 32px)
- Каждый комментарий может начинаться на новой странице независимо
- Длинные комментарии обрабатываются так же, как длинные посты

---

### 2. Freeze Layout

```mermaid
graph TD
    A[Page Array] --> B[For Each Page]
    B --> C[Render in Temp Container]
    C --> D[Get Element Bounds]
    D --> E[Convert to MM]
    E --> F[Make Relative to Page Top]
    F --> G[Apply position: absolute]
    G --> H[Save to pages table]
```

#### Алгоритм freeze

```javascript
async function freezePage(page, pageConfig) {
  const frozenElements = [];
  
  // 1. Находим первый элемент на странице (page-break)
  const pageTop = page.walls[0].container.getBoundingClientRect().top;
  
  // 2. Для каждого wall на странице
  page.walls.forEach(wall => {
    // Обрабатываем main post
    const postRect = wall.mainPost.getBoundingClientRect();
    frozenElemPosts = [];
  
  // 1. Получаем координаты самой страницы (page.element из Paged.js)
  const pageRect = page.element.getBoundingClientRect();
  
  // Координаты будут относительно начала страницы, а не viewport!
  
  // 2. Для каждого поста/комментария на странице
  page.items.forEach(item => {
    const container = item.element;
    const containerRect = container.getBoundingClientRect();
    
    // Вычитаем координаты страницы - получаем относительные координаты!
    const postBounds = {
      top: pxToMm(containerRect.top - pageRect.top) + pageConfig.margins.top,
      left: pxToMm(containerRect.left - pageRect.left) + pageConfig.margins.left,
      width: pxToMm(containerRect.width),
      height: pxToMm(containerRect.height)
    };
    
    // Структура поста в frozen layout
    const frozenPost = {
      telegram_id: item.data.telegram_id,
      type: item.isComment ? 'comment' : 'post',
      parent_post_id: item.parentPostId || null,
      bounds: postBounds,
      elements: []
    };
    
    // 3. Извлекаем вложенные элементы
    
    // Текстовые блоки
    const textElements = container.querySelectorAll('p, .post-body, .post-header');
    textElements.forEach(el => {
      const rect = el.getBoundingClientRect();
      frozenPost.elements.push({
        type: 'text',
        selector: el.className,
        bounds: {
          top: pxToMm(rect.top - pageRect.top) + pageConfig.margins.top,
          left: pxToMm(rect.left - pageRect.left) + pageConfig.margins.left,
          width: pxToMm(rect.width),
          height: pxToMm(rect.height)
        },
        content: el.textContent.trim()
      });
    });
    
    // Изображения
    const imageElements = container.querySelectorAll('img');
    imageElements.forEach(el => {
      const rect = el.getBoundingClientRect();
      frozenPost.elements.push({
        type: 'image',
        selector: el.className,
        bounds: {
          top: pxToMm(rect.top - pageRect.top) + pageConfig.margins.top,
          left: pxToMm(rect.left - pageRect.left) + pageConfig.margins.left,
          width: pxToMm(rect.width),
          height: pxToMm(rect.height)
        },
        src: el.src,
        alt: el.alt
      });
    });
    
    // Галереи
    const galleryContainers = container.querySelectorAll('.gallery-container');
    galleryContainers.forEach(gallery => {
      const rect = gallery.getBoundingClientRect();
      const galleryItems = gallery.querySelectorAll('.gallery-item');
      
      frozenPost.elements.push({
        type: 'gallery',
        bounds: {
          top: pxToMm(rect.top - pageRect.top) + pageConfig.margins.top,
          left: pxToMm(rect.left - pageRect.left) + pageConfig.margins.left,
          width: pxToMm(rect.width),
          height: pxToMm(rect.height)
        },
        items: Array.from(galleryItems).map(item => {
          const itemRect = item.getBoundingClientRect();
          const img = item.querySelector('img');
          return {
            bounds: {
              top: pxToMm(itemRect.top - pageRect.top) + pageConfig.margins.top,
              left: pxToMm(itemRect.left - pageRect.left) + pageConfig.margins.left,
              width: pxToMm(itemRect.width),
              height: pxToMm(itemRect.height)
            },
            src: img?.src,
            alt: img?.alt
          };
        })
      });
    });
    
    frozenPosts.push(frozenPost);
  });
  
  return {
    page_number: page.number,
    posts: frozenPoslute Positioning

#### Рекомендуемые библиотеки

**1. Paged.js** ⭐ (ЛУЧШИЙ ВАРИАНТ)
```bash
npm install pagedjs
```

**Возможности:**
- ✅ Автоматическая пагинация HTML
- ✅ Поддержка CSS @page rules
- ✅ Hooks для извлечения координат
- ✅ Создан специально для print layouts

**Использование:**
```javascript
import Paged from 'pagedjs';

const paged = new Paged.Previewer();

// Рендерим с пагинацией
await paged.preview(content, ['styles-pdf.css'], document.body);

// Извлекаем координаты
const pages = paged.chunker.pages;
pages.forEach(page => {
  const elements = page.element.querySelectorAll('.post, .group');
  elements.forEach(el => {
    const bounds = el.getBoundingClientRect();
    // Преобразуем в absolute
    el.style.position = 'absolute';
    el.style.top = `${bounds.top}px`;
    el.style.left = `${bounds.left}px`;
  });
});
```

**2. html2canvas + jsPDF**
```bash
npm install html2canvas jspdf
```

**Возможности:**
- ✅ Рендер DOM в canvas
- ✅ Точные координаты элементов
- ❌ Не очень подходит для text editing

**3. CSS Grid/Flexbox + Custom Paginator**
```javascript
// Собственная реализация без библиотек
class PageLayoutEngine {
  constructor(pageCon (обновленная):**
```json
{
  "version": "1.0",
  "channel_id": "llamasass",
  "page_size": "A4",
  "margins": [20, 20, 20, 20],
  "pages": [
    {
      "number": 1,
      "posts": [
        {
          "telegram_id": "2344",
          "type": "post",
          "parent_post_id": null,
          "bounds": {
            "top": 20,
            "left": 20,
            "width": 170,
            "height": 80
          },
          "elements": [
            {
              "type": "text",
              "selector": "post-body",
              "bounds": {"top": 25, "left": 35, "width": 140, "height": 30},
              "content": "Текст поста..."
            },
            {
              "type": "image",
              "selector": "post-media",
              "bounds": {"top": 60, "left": 20, "width": 170, "height": 100},
              "src": "/downloads/llamasass/media/2344_media.jpg"
            }
          ]
        },
        {
          "telegram_id": "5286",
          "type": "comment",
          "parent_post_id": "2344",
          "bounds": {
            "top": 180,
            "left": 28.47,
            "width": 161.53,
            "height": 40
          },
          "elements": [
            {
              "type": "text",
              "selector": "post-body",
              "bounds": {"top": 185, "left": 43.47, "width": 130, "height": 20},
              "content": "Текст комментария..."
            }
          ]
        }
      ]
    },
    {
      "number": 2,
      "posts": [
        {
          "telegram_id": "5287",
          "type": "comment",
          "parent_post_id": "2344",
          "bounds": {
            "top": 20,
            "left": 28.47,
            "width": 161.53,
            "height": 40
          },
          "elements": [
            {
              "type": "text",
              "selector": "post-body",
              "bounds": {"top": 25, "left": 43.47, "width": 130, "height": 20},
              "content": "Еще один комментарий на следующей странице..."
            }
          ]type": "post",
          "telegram_id": "2344",
          "bounds": {
            "top": 20,
            "left": 20,
            "width": 170,
            "height": 50
          },
          "children": [
            {
              "type": "text",
              "bounds": {"top": 20, "left": 20, "width": 170, "height": 30},
              "content": "Текст поста..."
            },
            {
              "type": "image",
              "bounds": {"top": 55, "left": 20, "width": 170, "height": 100},
              "src": "/downloads/llamasass/media/2344_media.jpg"
            }
          ]
        },
        {
          "type": "comment",
          "telegram_id": "5286",
          "parent_id": "2344",
          "bounds": {
            "top": 180,
            "left": 40,
            "width": 150,
            "height": 30
          }
        }
      ]
    }
  ]
}
```

---

## 🚀 PHASE 1: PAGINATION (Пошаговый план)

### Архитектура
- **Route:** `/preview/:channelId` с пустым layout (без navbar/sidebar)
- **Библиотека:** Paged.js для автоматической пагинации
- **Lazy loading:** По 20 страниц за раз
- **Backend API:** Получение постов с комментариями

### Шаг 1: Установка Paged.js
```bash
cd tg-offliner-frontend
npm install pagedjs
```
**Проверка:** В `package.json` должна появиться запись `"pagedjs": "^0.5.0"`

### Шаг 2: Создать пустой layout
**Файл:** `app/layouts/empty.vue`
```vue
<template>
  <div>
    <slot />
  </div>
</template>
```
**Проверка:** Открыть любую страницу с `definePageMeta({ layout: 'empty' })` - не должно быть navbar/sidebar

### Шаг 3: Создать preview route
**Файл:** `app/pages/preview/[channelId].vue`
- Layout: 'empty'
- Загружает посты канала через API
- Пока без пагинации - просто flow layout

**Проверка:** `/preview/llamasass` показывает посты в чистом виде

### Шаг 4: Backend API endpoint
**Файл:** `api/posts.py`
**Endpoint:** `GET /api/channels/<channel_id>/posts-with-comments`
- Возвращает посты + их комментарии
- Учитывает hidden флаг
- Сортировка по дате

**Проверка:** `curl http://localhost:5000/api/channels/llamasass/posts-with-comments`

### Шаг 5: Функция flattenPostsAndComments()
**Файл:** `app/utils/pagination.js`
- Алгоритм из документации
- Плоский список для Paged.js

**Проверка:** Console.log показывает плоский массив с флагами isComment

### Шаг 6: Composable usePaged()
**Файл:** `app/composables/usePaged.js`
- Функция `paginateContent(element, config)`
- Использует Paged.Previewer
- Возвращает массив pages

**Проверка:** Логи "Page 1", "Page 2" в консоли

### Шаг 7: Интегрировать пагинацию
- Добавить пагинацию в preview route
- Навигация "Previous" / "Next"
- Отображение номера страницы

**Проверка:** Можно листать страницы

### Шаг 8: Lazy loading
- Загрузка первых 20 страниц
- Кнопка "Load more pages"
- Подгрузка следующих 20

**Проверка:** Не тормозит при большом канале

### Шаг 9: Тестирование
- ✅ Комментарии с отступом ml-8
- ✅ Каждый пост/комментарий может быть на новой странице
- ✅ Длинные посты логируют warning
- ✅ Навигация плавная

---

## PHASE 2: FREEZE LAYOUT

### Этап 2: Freeze Layout (Промежуточная цель)

**Задачи:**
1. ✅ Установить Paged.js
2. ✅ Создать Preview Mode с пагинацией
3. ✅ Реализовать группировку постов с комментариями
4. ✅ Добавить page-break индикаторы
5. ✅ Реализовать lazy loading (20 страниц)

**API Endpoints:**
- `GET /api/channels/<channel_id>/pages?page=1&limit=20` - Получить страницы
- `POST /api/channels/<channel_id>/paginate` - Создать пагинацию

**Frontend Components:**
- `PagedPreview.vue` - Компонент с пагинированным preview
- `PageNavigator.vue` - Навигация по страницам
- `usePagination.js` - Composable для пагинации

**Frontend Routes:**
- `/preview/:channelId` - **Чистый preview** для пагинации (layout: 'empty', без navbar/sidebar)
- `/channels/:id` - Обычная страница канала с UI

**Критерии успеха:**
- [ ] Контент разбит на страницы по высоте
- [ ] Посты с комментариями не разделяются
- [ ] Lazy loading работает
- [ ] Видны page-break маркеры

---

### Этап 2: Freeze Layout

**Задачи:**
1. ✅ Реализовать функцию `freezePage()`
2. ✅ Конвертация px → mm
3. ✅ Сохранение в БД (таблица pages)
4. ✅ UI для freeze/unfreeze
5. ✅ Preview frozen layout

**API Endpoints:**
- `POST /api/channels/<channel_id>/freeze` - Заморозить layout
- `GET /api/channels/<channel_id>/frozen` - Получить frozen layout
- `DELETE /api/channels/<channel_id>/frozen` - Удалить frozen layout

**Frontend Components:**
- `FrozenLayout.vue` - Отображение frozen layout
- `FreezeButton.vue` - Кнопка freeze/unfreeze
- `useFreeze.js` - Composable для freeze logic

**Критерии успеха:**
- [ ] Координаты извлечены из DOM
- [ ] Преобразованы в миллиметры
- [ ] Сохранены в БД
- [ ] Preview показывает absolute positioning
- [ ] Визуально идентично flow layout

---

### Этап 3: PDF Export (Промежуточная цель)

**Задачи:**
1. ✅ Использовать frozen layout для PDF
2. ✅ WeasyPrint с absolute coordinates
3. ✅ Проверка соответствия preview

**API Endpoints:**
- `GET /api/channels/<channel_id>/export-pdf-frozen` - PDF из frozen layout

**Критерии успеха:**
- [ ] PDF создается из frozen layout
- [ ] Визуально идентичен preview
- [ ] Координаты точные (±1mm)

---

### Этап 4: IDML Export (Конечная цель)

**Задачи:**
1. ✅ IDMLBuilder использует frozen layout
2. ✅ Преобразование mm → points
3. ✅ Создание TextFrames/Rectangles по координатам
4. ✅ Проверка соответствия preview

**API Endpoints:**
- `GET /api/channels/<channel_id>/export-idml-frozen` - IDML из frozen layout

**Python:**
```python
def export_idml_from_frozen(channel_id):
    # Получаем frozen pages из БД
    pages_records = Page.query.filter_by(channel_id=channel_id).all()
    
    for page_record in pages_records:
        frozen_data = page_record.json_data
        
        for page in frozen_data['pages']:
            builder.add_page()
            
            for element in page['elements']:
                # Конвертируем mm → points
                bounds_pt = [
                    mm_to_points(element['bounds']['top']),
                    mm_to_points(element['bounds']['left']),
                    mm_to_points(element['bounds']['top'] + element['bounds']['height']),
                    mm_to_points(element['bounds']['left'] + element['bounds']['width'])
                ]
                
                if element['type'] == 'text':
                    builder.add_text_frame_absolute(
                        element['content'],
                        bounds_pt
                    )
                elif element['type'] == 'image':
                    builder.add_image_frame_absolute(
                        element['src'],
                        bounds_pt
                    )
```

**Критерии успеха:**
- [ ] IDML создается из frozen layout
- [ ] Открывается в InDesign без ошибок
- Очень длинные посты/комментарии могут не поместиться на одну страницу (в текущей версии просто переносятся целиком)
- Frozen layout привязан к page_size (re-freeze при смене формата)
- Максимум 20 страниц за раз (можно увеличить)
- Разбиение контента поста на части между страницами не реализовано (но технически возможно
---

## 📊 Структура файлов

```
tg-offliner/
├── api/
│   ├── pages.py                    # Существует, добавим методы
│   └── channels.py                 # Обновим для frozen export
├── idml_export/
│   └── builder.py                  # Добавим методы для frozen
├── tg-offliner-frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── PagedPreview.vue    # НОВЫЙ
│   │   │   ├── FrozenLayout.vue    # НОВЫЙ
│   │   │   ├── PageNavigator.vue   # НОВЫЙ
│   │   │   └── FreezeButton.vue    # НОВЫЙ
│   │   ├── composables/
│   │   │   ├── usePagination.js    # НОВЫЙ
│   │   │   └── useFreeze.js        # НОВЫЙ
│   │   ├── services/
│   │   │   └── pagesService.js     # НОВЫЙ
│   │   └── utils/
│   │       └── pageLayout.js       # НОВЫЙ
│   └── package.json                # Добавим pagedjs
└── FREEZE_LAYOUT_SPEC.md           # Этот документ
```

---

## 🧪 Тестирование
**Разбиение длинных постов на части между страницами** (split text/content across pages)
- Поддержка разных page orientations (portrait/landscape)
- Экспорт в другие форматы (DOCX, InCopy)

### FAQ

**Q: Можно ли разбить контент поста на несколько страниц?**  
A: **Технически - да, возможно!** Это требует дополнительной логики:
- Разделение текста на части по высоте страницы
- Перенос части элементов на следующую страницу
- Сохранение связи между частями одного поста
- Визуальные индикаторы продолжения (например, "...продолжение на стр. X")

Примеры реализации:
- Paged.js поддерживает `break-inside: avoid` и может разбивать контент
- CSS Fragmentation Module Level 3 (`break-before`, `break-after`, `break-inside`)
- Ручное разделение через измерение высоты и создание виртуальных "частей" поста

В текущей версии не включено в план, но можно добавить в Future Improvements.страницы
- [ ] `groupPostsWithComments()` - группировка
- [ ] `freezePage()` - freeze координат
- [ ] `pxToMm()` - конвертация единиц
- [ ] `mmToPoints()` - конвертация для IDML

### Integration Tests
- [ ] API `/api/channels/<id>/paginate`
- [ ] API `/api/channels/<id>/freeze`
- [ ] API `/api/channels/<id>/export-pdf-frozen`
- [ ] API `/api/channels/<id>/export-idml-frozen`

### E2E Tests
- [ ] Полный flow: Import → Paginate → Freeze → Export PDF
- [ ] Полный flow: Import → Paginate → Freeze → Export IDML
- [ ] Lazy loading страниц
- [ ] Визуальное сравнение Preview vs PDF vs IDML

---

## 📝 Заметки

### Производительность
- Обрабатываем по 20 страниц за раз
- Кешируем frozen layouts в БД
- Используем виртуализацию для больших каналов

### Limitations
- Пост + комментарии - неделимый блок (может не поместиться на странице)
- Frozen layout привязан к page_size (re-freeze при смене формата)
- Максимум 20 страниц за раз (можно увеличить)

### Future Improvements
- Интерактивное редактирование frozen layout (drag & drop)
- Умное разбиение больших блоков (пост + комментарии)
- Поддержка разных page orientations (portrait/landscape)
- Экспорт в другие форматы (DOCX, InCopy)

---

## 🎉 Готово!

Эта спецификация покрывает все аспекты freeze layout feature. Теперь можно приступать к реализации!
