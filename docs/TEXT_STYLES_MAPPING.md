# Сопоставление текстовых стилей: Preview (CSS) vs IDML

## Источники стилей

| Компонент | Файл | Описание |
|-----------|------|----------|
| **IDML стили** | `idml_export/styles.py` | Paragraph/Character/Object стили для InDesign |
| **IDML константы** | `idml_export/constants.py` | `PARAGRAPH_STYLES`, `FONTS` |
| **Единый конфиг** | `print-config.json` | Шрифты, размеры, конвертация единиц |
| **CSS preview** | `assets/tailwind.css` | Кастомные стили для preview/PDF |
| **Tailwind основной** | `tailwind.config.js` | `fontFamily`, `font-sans`/`font-serif`/`font-mono` |
| **Tailwind PDF** | `tailwind.pdf.config.js` | Наследует шрифты, отключает лишние плагины |

---

## Шрифты

| Параметр | Preview (CSS) | IDML | Источник IDML |
|----------|---------------|------|---------------|
| **Основной** | `Roboto`, `Arial`, `sans-serif` (Tailwind `font-sans`) | `Arial` | `print-config.json` → `fonts.body` |
| **Код** | `Courier New`, `monospace` (Tailwind `font-mono`) | `Courier New` | `fonts.code` |
| **Заголовки** | `Roboto` (тот же `font-sans`) | `Arial` | `fonts.heading` |
| **Emoji** | Системный | `Segoe UI Emoji` | `fonts.emoji` |

**⚠️ Расхождение:** Preview использует **Roboto** (Google Fonts, первый в стеке `font-sans`), IDML использует **Arial** (из `print-config.json`).

---

## Размер текста поста (PostBody)

| Параметр | Preview (CSS) | IDML | Расхождение |
|----------|---------------|------|-------------|
| **Размер (экран)** | `text-base` = **16px** | — | — |
| **Размер (печать)** | `print:text-sm` = **14px** (~10.5pt) | **10pt** (~13.3px) | ~1pt |
| **line-height (экран)** | `leading-relaxed` = **1.625** | — | — |
| **line-height (печать)** | `print:leading-normal` = **1.5** | Не задан (InDesign default ~**1.2**) | **Существенно** |
| **Цвет** | `print:text-black` | `Color/Black` | ✅ Совпадает |
| **letter-spacing** | `print:tracking-normal` = **0** | Не задан (0) | ✅ Совпадает |
| **SpaceAfter** | CSS `margin-bottom: 1em` между `<p>` | `SpaceAfter: 12pt` | Зависит от размера шрифта |

**Классы в PostBody.vue:**
```html
<div class="post-message font-sans text-base print:text-sm leading-relaxed print:leading-normal print:text-black print:tracking-normal">
```

---

## Дата (PostDate)

| Параметр | Preview (CSS) | IDML | Расхождение |
|----------|---------------|------|-------------|
| **Размер** | `text-xs` = **12px** (~9pt) | **9pt** (~12px) | ✅ ~Совпадает |
| **Цвет** | `text-gray-400` (#9ca3af) | `Color/Gray` | Зависит от определения Gray в IDML |
| **Выравнивание** | `ml-auto` (right) | `RightAlign` | ✅ Совпадает |
| **SpaceAfter** | — | `4pt` | — |

**Классы в PostHeader.vue:**
```html
<span class="post-date ml-auto text-xs text-gray-400">
```

---

## Автор (Author)

| Параметр | Preview (CSS) | IDML | Расхождение |
|----------|---------------|------|-------------|
| **Размер** | Через PostAuthor компонент | **13pt** | Нужно проверить |
| **Стиль** | `font-bold` (если есть) | `FontStyle: Bold` | — |
| **SpaceAfter** | — | `4pt` | — |

---

## Character Styles (inline форматирование)

| Telegram Entity | Preview (CSS) | IDML Style | IDML шрифт/размер |
|-----------------|---------------|------------|---------------------|
| `MessageEntityBold` | `<b>` / `font-bold` | `TelegramBold` | Определён в styles.py |
| `MessageEntityItalic` | `<i>` / `italic` | `TelegramItalic` | — |
| `MessageEntityCode` | `<code>` / `font-mono` | `TelegramCode` | `Courier New`, 9pt |
| `MessageEntityPre` | `<pre>` / `font-mono` | `TelegramCodeBlock` | `Courier New`, 9pt |
| `MessageEntityTextUrl` | `<a>` | `TelegramLink` | — |
| `MessageEntityUrl` | `<a>` | `TelegramLink` | — |
| `MessageEntityMention` | `<a>` | `TelegramMention` | — |
| `MessageEntityStrike` | `<s>` | `TelegramStrike` | — |
| `MessageEntityUnderline` | `<u>` | `TelegramUnderline` | — |

Маппинг entity → IDML style определён в `idml_export/constants.py` → `ENTITY_TO_CHAR_STYLE`.

---

## Paragraph Styles (полный список из constants.py)

| Стиль | Шрифт | Размер | Цвет | SpaceAfter | Доп. параметры |
|-------|-------|--------|------|------------|----------------|
| `PostDate` | Arial | 9pt | Gray | 4pt | — |
| `PostHeader` | Arial | 9pt | Gray | 6pt | — |
| `PostBody` | Arial | 10pt | Black | 12pt | — |
| `PostQuote` | Arial | 10pt | DarkGray | 12pt | `left_indent: 14.17pt` (5mm) |
| `PostFooter` | Arial | 8pt | Gray | 20pt | — |

---

## Главные расхождения и как их исправить

### 1. Шрифт: Roboto vs Arial
- **Причина:** `tailwind.config.js` ставит Roboto первым, `print-config.json` указывает Arial
- **Исправление:** Либо поменять `print-config.json` → `fonts.body: "Roboto"`, либо в Tailwind конфиге поставить Arial первым

### 2. Line-height (интерлиньяж)
- **CSS:** 1.5 (print), 1.625 (screen)
- **IDML:** не задан → InDesign default ~1.2 (120%)
- **Исправление:** В `styles.py` добавить `Leading` или `AutoLeading` в paragraph styles

### 3. Размер текста PostBody
- **CSS print:** 14px (~10.5pt)
- **IDML:** 10pt (~13.3px)
- **Исправление:** Унифицировать через `print-config.json` → `fonts.bodySize`

### 4. SpaceAfter vs margin
- **CSS:** `margin-bottom: 1em` между `<p>` (зависит от font-size)
- **IDML:** фиксированное значение в points
- **Исправление:** Рассчитать `SpaceAfter = bodySize * 1.0` для эквивалента `1em`

---

## Где менять стили

### Для IDML:
1. **Шрифты и размеры** → `print-config.json` → секция `fonts`
2. **Paragraph Styles** → `idml_export/constants.py` → `PARAGRAPH_STYLES`
3. **XML стили** → `idml_export/styles.py` → `_create_paragraph_styles()`, `_create_character_styles()`

### Для Preview/PDF:
1. **Шрифты** → `tailwind.config.js` → `fontFamily`
2. **Классы** → Vue компоненты (`PostBody.vue`, `PostHeader.vue`)
3. **Кастомные стили** → `assets/tailwind.css`

### Единый источник правды:
- `print-config.json` — шрифты, размеры страниц, margins, единицы конвертации
- Читается Python: `idml_export/constants.py`
- Читается JS: `app/utils/units.js`

---

**Версия:** 1.0  
**Дата:** 26 февраля 2026
