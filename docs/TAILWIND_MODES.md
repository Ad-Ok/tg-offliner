# Tailwind Display Modes: paper & minimal

## 🎯 Концепция

Используем Tailwind кастомные варианты для управления отображением в разных режимах через `data-mode` атрибут.

## 📋 Режимы

| Режим | URL | data-mode | Tailwind вариант | Использование |
|-------|-----|-----------|------------------|---------------|
| **Default (Web)** | `/posts/channel` | `"default"` | базовые классы | Обычный веб |
| **Paper (PDF)** | `/preview/channel?export=pdf` | `"paper"` | `paper:` | PDF preview |
| **Minimal (IDML)** | `/preview/channel?export=idml` | `"minimal"` | `minimal:` | IDML preview |
| **Browser Print** | Ctrl+P | — | `paper:` | @media print |

## 🔧 Установка

### 1. Tailwind config (✅ Уже настроено)

```js
// tailwind.config.js
const plugin = require('tailwindcss/plugin')

module.exports = {
  plugins: [
    plugin(function({ addVariant }) {
      // paper: - для PDF preview + браузерная печать
      addVariant('paper', [
        '[data-mode="paper"] &',
        '@media print'
      ])
      
      // minimal: - для IDML preview
      addVariant('minimal', '[data-mode="minimal"] &')
    })
  ]
}
```

### 2. Composable (✅ Уже создан)

```js
// app/composables/useDisplayMode.js
const { currentMode, isPaperMode, isMinimalMode, isExportMode } = useDisplayMode()
```

### 3. Root element (✅ Уже настроено)

```vue
<!-- app/app.vue -->
<div :data-mode="currentMode">
  <NuxtPage />
</div>
```

## 🎨 Использование в компонентах

### Базовый пример

```vue
<template>
  <!-- Скрыть в paper и minimal -->
  <div class="paper:hidden minimal:hidden">
    Footer / Reactions / Editor
  </div>
  
  <!-- Разные стили для разных режимов -->
  <div class="
    p-4 bg-white shadow-lg border rounded-lg
    paper:p-2 paper:shadow-none paper:border-gray-300
    minimal:p-0 minimal:bg-transparent minimal:border-0
  ">
    Content
  </div>
</template>
```

### Post.vue пример

```vue
<template>
  <div class="post-container">
    <!-- Editor: скрыт в экспортных режимах -->
    <PostEditor 
      class="paper:hidden minimal:hidden"
      :post="post" 
    />
    
    <div class="post w-full font-sans">
      <!-- Post wrapper: разные стили -->
      <div class="
        p-4 bg-white dark:bg-black 
        border tweet-border rounded-lg shadow-sm
        paper:p-3 paper:shadow-none paper:border-gray-300
        minimal:p-0 minimal:bg-transparent minimal:border-0
      ">
        <PostHeader />
        <PostBody />
        
        <!-- Media: разные отступы -->
        <div class="mt-2 pl-11 paper:pl-0 minimal:pl-0">
          <PostMedia />
        </div>
      </div>

      <!-- Footer: скрыт в экспорте -->
      <PostFooter class="paper:hidden minimal:hidden" />
    </div>
  </div>
</template>
```

### Nested data-mode (детальная кастомизация)

```vue
<template>
  <!-- Корневой data-mode="paper" -->
  <div data-mode="paper">
    <div class="p-4 paper:p-2">
      Standard paper styles
      
      <!-- Вложенный data-mode="minimal" переопределяет -->
      <div data-mode="minimal" class="border-2 paper:border minimal:border-0">
        Minimal styles applied here
      </div>
    </div>
  </div>
</template>
```

## 🔍 Частые паттерны

### Скрыть UI элементы

```vue
<!-- Кнопки, редакторы, интерактив -->
<button class="paper:hidden minimal:hidden">Edit</button>
<div class="controls paper:hidden minimal:hidden">Controls</div>
```

### Сбросить декоративные стили

```vue
<div class="
  shadow-lg rounded-xl border-2 
  paper:shadow-none paper:rounded-none paper:border
  minimal:shadow-none minimal:rounded-none minimal:border-0
">
  Content
</div>
```

### Изменить отступы

```vue
<!-- Убрать левый отступ для медиа -->
<div class="pl-11 paper:pl-0 minimal:pl-0">
  <img src="..." />
</div>

<!-- Уменьшить внутренние отступы -->
<div class="p-6 paper:p-3 minimal:p-0">
  Content
</div>
```

### Изменить размеры шрифта

```vue
<div class="text-base paper:text-sm minimal:text-xs">
  Text content
</div>
```

## 💡 Composable API

### useDisplayMode()

```js
import { useDisplayMode } from '~/composables/useDisplayMode'

const { 
  currentMode,     // 'default' | 'paper' | 'minimal'
  isPaperMode,     // boolean
  isMinimalMode,   // boolean
  isDefaultMode,   // boolean
  isExportMode     // boolean (paper || minimal)
} = useDisplayMode()
```

### Примеры использования

```vue
<script setup>
const { isPaperMode, isExportMode } = useDisplayMode()

// Условная логика
if (isExportMode.value) {
  // Логика для экспортных режимов
}
</script>

<template>
  <!-- Условный рендеринг -->
  <div v-if="!isExportMode">
    Interactive features
  </div>
  
  <!-- Условные классы (альтернатива Tailwind вариантам) -->
  <div :class="{ 'hidden': isPaperMode }">
    Paper-specific hidden
  </div>
</template>
```

## 🧪 Тестирование

### URLs для тестирования:

```bash
# Default mode
http://localhost:3000/posts/llamasass

# Paper mode (PDF)
http://localhost:3000/preview/llamasass?export=pdf

# Minimal mode (IDML)  
http://localhost:3000/preview/llamasass?export=idml

# Browser print (paper: также сработает)
Ctrl+P (Cmd+P на Mac)
```

### Проверка в DevTools:

```js
// Открыть консоль и проверить data-mode
document.querySelector('[data-mode]').getAttribute('data-mode')
// → "default" | "paper" | "minimal"
```

## 📊 Сравнение с print:

| Вариант | Когда срабатывает | Использование |
|---------|-------------------|---------------|
| `paper:` | `data-mode="paper"` + `@media print` | PDF preview + Ctrl+P |
| `minimal:` | `data-mode="minimal"` | IDML preview |
| `print:` | `@media print` только | Браузерная печать |

**Важно:** `paper:` заменяет `print:` для наших нужд, т.к. объединяет оба случая!

## ✅ Best Practices

1. **Используй `paper:` вместо `print:`** для единообразия
2. **Комбинируй варианты:** `paper:hidden minimal:hidden`
3. **Не дублируй:** если стили одинаковые для paper и minimal, вынеси в общий класс
4. **Nested data-mode:** используй для детальной кастомизации отдельных блоков
5. **Composable:** используй `isExportMode` для условной логики, а не дублируй в шаблоне

## 🚀 Миграция существующих компонентов

### Шаг 1: Найти print: классы

```bash
grep -r "print:" app/components/
```

### Шаг 2: Заменить на paper:

```vue
<!-- Было -->
<div class="print:hidden">

<!-- Стало -->
<div class="paper:hidden minimal:hidden">
```

### Шаг 3: Протестировать

- Default: визуально проверить
- Paper: добавить `?export=pdf` к URL
- Minimal: добавить `?export=idml` к URL

## 📝 Примеры из проекта

### SystemAlert (скрыть в экспорте)

```vue
<SystemAlert 
  class="paper:hidden minimal:hidden fixed top-16 right-4 z-50"
/>
```

### Navbar (скрыть в экспорте)

```vue
<nav class="paper:hidden minimal:hidden">
  <!-- navigation -->
</nav>
```

### Post wrapper (адаптивные стили)

```vue
<div class="
  post-wrap 
  p-4 bg-white border shadow-sm rounded-lg
  paper:p-3 paper:shadow-none paper:border-gray-300
  minimal:p-0 minimal:bg-transparent minimal:border-0
">
```

---

**Версия:** 1.0  
**Дата:** 30 декабря 2025
