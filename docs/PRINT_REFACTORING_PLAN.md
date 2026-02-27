# Рефакторинг Print-компонентов: Подробный план

## Цель

Унифицировать рендеринг постов для печати/экспорта: preview, frozen layout и IDML должны использовать одни и те же компоненты с одними стилями. Это обеспечит:
- Корректные координаты (freeze снимает bounds с тех же компонентов, что рендерит frozen)
- Единый источник стилей для всех экспортов
- Отсутствие дублирования кода между preview и frozen

---

## Текущее состояние

### Preview (index.vue)
- Использует веб-компоненты: `Post` → `PostHeader` + `PostBody` + `PostMedia`
- Компонент `Group` для галерей с `.gallery-container` + `.gallery-item`
- Стили: Tailwind классы `font-sans text-base print:text-sm leading-relaxed`
- `freezeCurrentLayout()` снимает bounds через `getBoundingClientRect()`

### Frozen (frozen.vue)
- **Полностью кастомный рендеринг**, не использует общие компоненты
- Свой вывод автора, даты, текста (голый `v-html`)
- Своя обработка ошибок
- Стили отличаются от preview → текст не совпадает с bounds

### IDML (builder.py)
- Третий набор стилей (Arial 10pt из print-config.json)
- Читает frozen layout bounds, но стили текста другие

### Проблема
Три рендерера с разными стилями → координаты из preview некорректны для frozen и IDML.

---

## Целевая архитектура

### Три атомарных компонента

```
components/print/
├── PrintText.vue     # .print-text — [author_name] + [date] + message
├── PrintAvatar.vue   # .print-avatar — img, круглое, float:left, опциональный
└── PrintMedia.vue    # .print-media — одно изображение, путь media/, border_width проп
```

**Галереи:** Галерея — это группа постов с `grouped_id`. Рендерится как
`PrintText` (текст первого поста) + `.gallery-container` с absolute-позиционированными
`.gallery-item`, внутри каждого — `<PrintMedia>`. Layout данные (`cells`, `border_width`)
приходят из Layout модели. Галерея НЕ требует отдельного компонента — это компоновка
PrintText + PrintMedia, определяемая layout-ом.

### Принципы
- Компоненты отвечают ТОЛЬКО за контент и стили (шрифт, размер, цвет, line-height)
- Positioning — ответственность layout-а (index.vue / frozen.vue)
- CSS-классы сохраняются для совместимости с `freezeCurrentLayout`
- Путь к медиа: `media/` (не `thumbs/`)
- **Стили строго через Tailwind классы!** Никаких секций `<style>` в компонентах

### Как рендерится каждый тип поста

> **Автор и дата — опциональны.** Текст и медиа выводятся всегда (если есть в данных).
> Компоненты должны корректно рендериться при любой комбинации присутствия/отсутствия автора и даты.

**Одиночный пост канала (без медиа):**
```
PrintText (date + message)
```

**Одиночный пост канала с картинкой:**
```
PrintText (date + message)
PrintMedia (одна картинка)
```

**Комментарий от стороннего автора (без даты):**
```
PrintAvatar (аватар автора)               ← рядом с текстом, float:left
PrintText (author_name + message)         ← showAuthor=true, showDate=false
PrintMedia (картинка)                     ← если есть
```

> Комментарий стороннего автора **по умолчанию НЕ включает дату**.

**Комментарий от стороннего автора с галереей (без даты):**
```
PrintAvatar (аватар автора)               ← рядом с текстом, float:left
PrintText (author_name + message)         ← showAuthor=true, showDate=false
gallery-container + PrintMedia × N        ← каждая картинка в gallery-item
```

**Галерея (grouped_id):**
```
PrintText (date + message первого поста)
gallery-container + PrintMedia × N (каждая картинка в gallery-item)
```

### Preview (index.vue) — flow layout
```vue
<div class="post-container" :data-post-id="post.telegram_id">
  <PrintAvatar v-if="showAuthor" :post="post" />
  <PrintText :post="post" :show-author="showAuthor" :show-date="showDate" />
  <PrintMedia v-if="hasSingleMedia" :post="post" />
</div>

<!-- Галерея -->
<div class="post-container" :data-grouped-id="groupedId">
  <PrintAvatar v-if="showAuthor" :post="firstPost" />
  <PrintText :post="firstPost" :show-date="showDate" :show-author="showAuthor" />
  <div class="gallery-container relative" :style="galleryContainerStyle">
    <div v-for="cell in layout.cells" class="gallery-item absolute" :style="cellStyle(cell)">
      <PrintMedia :post="postByIndex(cell.image_index)" :border-width="borderWidth" />
    </div>
  </div>
</div>
```

### Frozen (frozen.vue) — absolute layout

> **Без лишних обёрток!** Класс `absolute` и стили позиционирования применяются
> к корневому элементу самого компонента (через пропы `class` и `style`),
> а не через дополнительные `<div>`.

```vue
<div v-for="post in page.posts">
  <PrintText :post="getPostFromDb(post)" :show-author="post.showAuthor"
             class="absolute" :style="postBounds(post)" />
  <PrintAvatar v-if="post.avatar" :post="getPostFromDb(post)"
               class="absolute" :style="avatarBounds(post)" />
  <PrintMedia v-for="media in post.media" :post="getMediaPost(media)"
              :border-width="media.border_width"
              class="absolute" :style="mediaBounds(media)" />
</div>
```

---

## Фазы реализации

---

### Фаза 1: Создание Print-компонентов

Создаём три компонента с базовыми стилями. На этом этапе стили временные (Tailwind классы из существующих), будут уточнены в Фазе 5.

#### 1.1 PrintText.vue

**Файл:** `tg-offliner-frontend/app/components/print/PrintText.vue`

**Props:**
| Проп | Тип | Default | Описание |
|------|-----|---------|----------|
| `post` | Object | required | Объект поста из БД |
| `showAuthor` | Boolean | false | Показывать имя автора перед текстом |
| `showDate` | Boolean | true | Показывать дату |

**Структура:**
```vue
<template>
  <div class="print-text">
    <!-- Имя автора (опционально) -->
    <div v-if="showAuthor && post.author_name" class="print-author-name">
      {{ post.author_name }}
    </div>
    <!-- Дата (опционально) -->
    <div v-if="showDate && formattedDate" class="print-date">
      {{ formattedDate }}
    </div>
    <!-- Текст поста -->
    <div v-if="post.message" class="print-message post-message" v-html="post.message"></div>
  </div>
</template>
```

**CSS-классы для freeze:** `.print-text` (весь блок)

**Логика:**
- Форматирование даты: из `post.date` через `dateService` или inline
- `post.message` рендерится как HTML (сохраняем `v-html`)
- Класс `post-message` сохраняется для CSS правила `p:not(:last-child) { margin-bottom: 1em }`

#### 1.2 PrintAvatar.vue

**Файл:** `tg-offliner-frontend/app/components/print/PrintAvatar.vue`

**Props:**
| Проп | Тип | Default | Описание |
|------|-----|---------|----------|
| `avatarPath` | String | required | Путь к аватару (из post.author_avatar) |

**Структура:**
```vue
<template>
  <div class="print-avatar float-left mr-8">
    <img :src="avatarSrc" class="w-10 h-10 rounded-full object-cover" alt="Author" />
  </div>
</template>
```

> **Только Tailwind!** Все стили через классы: `float-left mr-8` для обтекания текстом,
> `w-10 h-10 rounded-full` для круглой формы. Никаких секций `<style>`.

**CSS-классы для freeze:** `.print-avatar`

**Логика:**
- Путь: `${mediaBase}/downloads/${avatarPath}`
- Стили: Tailwind классы — `float-left mr-8` (обтекание), `w-10 h-10 rounded-full` (форма)
- В IDML: `TextWrapPreference` с `BoundingBoxTextWrap`

#### 1.3 PrintMedia.vue

**Файл:** `tg-offliner-frontend/app/components/print/PrintMedia.vue`

**Props:**
| Проп | Тип | Default | Описание |
|------|-----|---------|----------|
| `post` | Object | required | Объект поста (нужны media_url, media_type, mime_type) |
| `borderWidth` | String/Number | '0' | Толщина рамки (для галерей) |

**Структура:**
```vue
<template>
  <div class="print-media post-media single-image" 
       :data-media-type="post.media_type" 
       :data-mime-type="post.mime_type">
    <img :src="mediaSrc" class="w-full h-full object-cover" alt="Media" :style="borderStyle" />
  </div>
</template>
```

**CSS-классы для freeze:** `.print-media`, `.post-media`, `.single-image`
- Сохраняем `.post-media.single-image` для обратной совместимости с `freezeCurrentLayout`

**Логика:**
- Путь: `${mediaBase}/downloads/${post.media_url}` — полноразмерное изображение, НЕ thumbnail
- `data-media-type` и `data-mime-type` — для `freezeCurrentLayout`
- `borderWidth` → `border: ${borderWidth}px solid white` (для галерей)

---

### Фаза 2: Интеграция в Preview (index.vue)

Заменяем веб-компоненты на Print-компоненты в режиме `minimal` (preview для печати).

#### 2.1 Анализ текущего index.vue

- Изучить как сейчас рендерятся посты и группы в `data-mode="minimal"`
- Определить точки интеграции (где Post заменяется на PrintText+PrintMedia)
- Определить как передаются данные (postsData, groupedPosts, layouts)

#### 2.2 Одиночные посты

Заменить рендеринг одиночного поста в minimal режиме:
- Вместо `<Post>` → `<PrintAvatar>` + `<PrintText>` + `<PrintMedia>`
- Сохранить `.post-container` обёртку с `data-post-id`, `data-channel-id`
- Сохранить `data-is-comment`, `data-date` атрибуты

#### 2.3 Галереи

Заменить рендеринг галерей (сейчас через `Group.vue`):
- `.gallery-container` с absolute-позиционированными `.gallery-item`
- Внутри каждого `gallery-item` → `<PrintMedia>` вместо `<PostMedia>`
- Layout данные (cells, border_width) используются как и раньше

#### 2.4 Обновить freezeCurrentLayout

Обновить селекторы в `freezeCurrentLayout()`:
- `.print-text` → bounds текстового блока
- `.print-avatar` → bounds аватара (если есть)
- `.print-media` / `.gallery-item` → bounds медиа (без изменений — классы сохранены)

Добавить в frozen data:
- `avatar` bounds (новое поле, если аватар есть)
- `showAuthor` флаг

#### 2.5 Условный рендеринг

Веб-компоненты (Post, PostBody, PostMedia) продолжают использоваться:
- На странице постов (`/[channelId]/posts`)
- В HTML экспорте
- В не-minimal режиме

Print-компоненты используются ТОЛЬКО в `data-mode="minimal"` на preview.

---

### Фаза 3: Интеграция в Frozen (frozen.vue)

Заменяем кастомный рендеринг на Print-компоненты.

#### 3.1 Замена текстового блока

Текущий код:
```vue
<div class="post-body">
  <div v-if="shouldShowAuthor(post)" class="post-author">...</div>
  <div v-if="post.date" class="post-date">...</div>
  <div class="post-message" v-html="..."></div>
</div>
```

Замена:
```vue
<PrintText :post="getPostFromDb(post)" :show-author="post.showAuthor"
           class="absolute" :style="postBounds(post)" />
```

> Класс `absolute` и стили позиционирования применяются к корневому элементу PrintText,
> без дополнительной обёртки `<div>`.

#### 3.2 Замена аватара

Текущий код рендерит аватар внутри post-body. Новый — отдельный absolute блок без обёртки:
```vue
<PrintAvatar v-if="post.avatar" :avatar-path="getPostFromDb(post).author_avatar"
             class="absolute" :style="avatarBounds(post)" />
```

#### 3.3 Замена медиа

Текущий код:
```vue
<div class="frozen-media absolute" :style="getMediaStyle(media)">
  <img :src="getMediaUrl(media, post)" class="w-full h-full object-cover" />
</div>
```

Замена:
```vue
<PrintMedia :post="getMediaPost(media)" :border-width="media.border_width"
            class="absolute" :style="mediaBounds(media)" />
```

#### 3.4 Удаление дублированной логики

Удалить из frozen.vue:
- `shouldShowAuthor()` — логика перенесена в данные (флаг `showAuthor` из freeze)
- `getAuthorAvatarUrl()` — внутри PrintAvatar
- `getMediaUrl()` — внутри PrintMedia

#### 3.5 Визуальное сравнение

Открыть preview и frozen рядом → убедиться что текст, аватары и медиа выглядят одинаково.

---

### Фаза 4: Тесты

#### 4.1 Unit-тесты Print-компонентов

Проверить рендеринг каждого компонента:
- PrintText: с автором / без автора / с датой / без даты / с HTML в message
- PrintAvatar: корректный src, круглая форма
- PrintMedia: корректный src из media/ (не thumbs/), border_width

#### 4.2 Тесты freeze → frozen

- Проверить что `freezeCurrentLayout` корректно снимает bounds с Print-компонентов
- Проверить что frozen data содержит `avatar` bounds и `showAuthor` флаг
- Проверить что frozen рендерит те же компоненты

#### 4.3 Регрессионные тесты

- Проверить что веб-компоненты (Post/PostBody/PostMedia) не сломаны на странице постов
- Проверить что HTML экспорт не затронут
- Проверить freeze → frozen → IDML pipeline на тестовом канале llamatest

#### 4.4 Тесты бекенда (если есть изменения в API)

- Проверить frozen layout API (`POST /api/pages/<channel_id>`, `GET /api/pages/<channel_id>/frozen`)
- Убедиться что новые поля (avatar bounds, showAuthor) сохраняются и читаются

---

<!-- ЗАКОММЕНТИРОВАНО: требует дополнительного обсуждения
### Фаза 5: Стили

Единый источник стилей для всех печатных форматов.

#### 5.1 Добавить print-* значения в tailwind.pdf.config.js

```js
// tailwind.pdf.config.js
theme: {
  extend: {
    fontSize: {
      'print-body': ['10pt', { lineHeight: '1.4' }],
      'print-date': ['9pt', { lineHeight: '1.2' }],
      'print-author': ['13pt', { lineHeight: '1.2' }],
    },
    fontFamily: {
      'print-body': ['PT Serif', 'Georgia', 'serif'],  // или другой шрифт
      'print-code': ['Courier New', 'monospace'],
    },
    spacing: {
      'print-avatar': '8mm',     // размер аватара
      'print-avatar-gap': '2mm', // отступ аватара от текста
    },
    // ...
  }
}
```

#### 5.2 Написать scripts/generate-print-config.js

Скрипт извлекает значения из Tailwind resolved config и генерирует `print-config.json`:
- fonts (body, code, heading, emoji)
- fontSize (body, date, author, header)
- lineHeight
- spacing (avatar size, gaps)
- pageSizes, margins, conversion constants

#### 5.3 Обновить npm scripts

```json
{
  "generate:print-config": "node scripts/generate-print-config.js",
  "build:pdf-css": "npm run generate:print-config && tailwindcss -c tailwind.pdf.config.js -i ./assets/tailwind.css -o ./public/styles-pdf.css --minify"
}
```

#### 5.4 Обновить Print-компоненты

Заменить временные Tailwind классы на `text-print-body`, `text-print-date`, `text-print-author`, `font-print-body` и т.д.

#### 5.5 Пересобрать styles-pdf.css

```bash
docker compose exec ssr sh -c "cd /app && npm run build:pdf-css"
```

#### 5.6 Визуальная проверка

Открыть preview → проверить что стили корректны → freeze → проверить frozen → сверить с ожиданиями.
-->

---

<!-- ЗАКОММЕНТИРОВАНО: требует дополнительного обсуждения
### Фаза 6: IDML синхронизация

#### 6.1 Обновить idml_export/constants.py

- Читает `print-config.json` (автосгенерированный)
- Убедиться что `FONTS`, `PARAGRAPH_STYLES` содержат актуальные значения

#### 6.2 Обновить idml_export/styles.py

- Добавить `Leading` (интерлиньяж) в paragraph styles из конфига
- Обновить размеры шрифтов из конфига
- Добавить `TextWrapPreference` для аватара (BoundingBoxTextWrap)

#### 6.3 Обновить idml_export/builder.py

- `add_frozen_post()`: читать новый формат frozen data (avatar bounds, showAuthor)
- Создавать Rectangle для аватара с `TextWrapPreference`
- Проверить что TextFrame и Rectangle bounds совпадают с frozen data

#### 6.4 Тестирование в InDesign

- Экспортировать IDML для llamatest
- Открыть в InDesign
- Проверить:
  - Позиционирование текста совпадает с frozen
  - Шрифт и размер текста из конфига
  - Аватары с обтеканием
  - Галереи с правильными border_width
  - Нет сдвигов/переполнений
-->

---

### Фаза 7: Чанки в preview (отдельная задача)

_Не входит в текущий рефакторинг. Выполняется после стабилизации Фаз 1-6._

#### 7.1 usePreviewChunks composable
#### 7.2 Итеративный freeze (чанк за чанком)
#### 7.3 Тестирование на большом канале

---

## Зависимости между фазами

```
Фаза 1 (компоненты) → Фаза 2 (preview) → Фаза 3 (frozen) → Фаза 4 (тесты)
                                                                      ↓
                                                        Фаза 5 (стили) — ⏸️ TBD
                                                                      ↓
                                                        Фаза 6 (IDML) — ⏸️ TBD
                                                                      ↓
                                                               Фаза 7 (чанки)
```

- Фазы 1-3 меняют структуру, минимально трогают стили
- Фаза 4 фиксирует корректность новой структуры
- Фаза 5 настраивает финальные стили
- Фаза 6 синхронизирует IDML с новой системой
- Фаза 7 полностью независима

---

## Файлы, которые будут затронуты

### Новые файлы
- `tg-offliner-frontend/app/components/print/PrintText.vue`
- `tg-offliner-frontend/app/components/print/PrintAvatar.vue`
- `tg-offliner-frontend/app/components/print/PrintMedia.vue`
- `scripts/generate-print-config.js` (Фаза 5 — ⏸️ TBD)

### Изменяемые файлы
- `tg-offliner-frontend/app/pages/preview/[channelId]/index.vue` — Фаза 2
- `tg-offliner-frontend/app/pages/preview/[channelId]/frozen.vue` — Фаза 3
- `tg-offliner-frontend/tailwind.pdf.config.js` — Фаза 5
- `tg-offliner-frontend/package.json` — Фаза 5 (npm script)
- `idml_export/styles.py` — Фаза 6
- `idml_export/constants.py` — Фаза 6
- `idml_export/builder.py` — Фаза 6

### Не изменяемые файлы
- `tg-offliner-frontend/app/components/Post.vue` — остаётся для веб-версии
- `tg-offliner-frontend/app/components/PostBody.vue` — остаётся для веб-версии
- `tg-offliner-frontend/app/components/PostMedia.vue` — остаётся для веб-версии
- `tg-offliner-frontend/app/components/PostHeader.vue` — остаётся для веб-версии
- `tg-offliner-frontend/app/components/Group.vue` — остаётся для веб-версии

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Сломать веб-версию постов | Низкая | Print-компоненты изолированы, веб-компоненты не меняются |
| Сломать HTML экспорт | Низкая | HTML экспорт использует веб-компоненты, не затрагивается |
| Несовпадение bounds preview ↔ frozen | Средняя | Визуальное сравнение на каждой фазе |
| Tailwind не поддерживает pt в fontSize | Низкая | Tailwind позволяет произвольные строки в конфиге |
| InDesign не поддерживает выбранный шрифт | Средняя | Использовать системные шрифты (Arial, Georgia, PT Serif) |

---

**Версия:** 1.1
**Дата:** 27 февраля 2026
