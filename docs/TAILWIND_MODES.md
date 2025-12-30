# Tailwind Display Modes: print & minimal

## 🎯 Концепция

Используем Tailwind варианты для управления отображением в разных режимах:
- **Встроенный `print:`** — для браузерной печати и PDF генерации
- **Кастомный `minimal:`** — для IDML preview через `data-mode` атрибут

## 📋 Режимы

| Режим | Где используется | data-mode | Tailwind вариант | Описание |
|-------|------------------|-----------|------------------|----------|
| **Default (Web)** | Везде по умолчанию | `"default"` | базовые классы | Обычный веб-интерфейс |
| **Print (PDF)** | При печати и PDF генерации | — | `print:` | `@media print` (встроенный в Tailwind) |
| **Minimal (IDML)** | `/preview/{channel}` | `"minimal"` | `minimal:` | Preview для IDML экспорта |

## 🔄 Workflow экспорта:

1. **PDF экспорт** → Кнопка "Экспорт в PDF" → Сразу скачивается PDF (без preview)
2. **IDML экспорт** → Кнопка "Экспорт в IDML" → Открывает `/preview/{channel}` с `minimal` режимом → Пользователь проверяет → Экспортирует из preview

## 🔧 Установка

### 1. Tailwind config (✅ Уже настроено)

```js
// tailwind.config.js
const plugin = require('tailwindcss/plugin')

module.exports = {
  plugins: [
    plugin(function({ addVariant }) {
      // minimal: - для IDML preview
      addVariant('minimal', '[data-mode="minimal"] &')
    })
  ]
}
```

**Примечание:** Вариант `print:` уже встроен в Tailwind и работает через `@media print`. Не нужно его добавлять!

### 2. useDisplayMode composable (✅ Уже настроено)

```js
// app/composables/useDisplayMode.js
export const useDisplayMode = () => {
  const route = useRoute()
  
  const currentMode = computed(() => {
    if (route.path.startsWith('/preview/')) return 'minimal'
    return 'default'
  })
  
  const isMinimalMode = computed(() => currentMode.value === 'minimal')
  const isDefaultMode = computed(() => currentMode.value === 'default')
  
  return {
    currentMode,
    isMinimalMode,
    isDefaultMode
  }
}
```

### 3. Root element (✅ Уже настроено)

```vue
<!-- app/app.vue -->
<div :data-mode="currentMode">
  <NuxtPage />
</div>
```

**Примечание:** `data-mode` нужен только для `minimal` варианта. Вариант `print:` работает автоматически через @media print.

## 🎨 Использование в компонентах

### Базовый пример

```vue
<template>
  <!-- Скрыть в print и minimal -->
  <div class="print:hidden minimal:hidden">
    Footer / Reactions / Editor
  </div>
  
  <!-- Разные стили для разных режимов -->
  <div class="
    p-4 bg-white shadow-lg border rounded-lg
    print:p-2 print:shadow-none print:border-gray-300
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
      class="print:hidden minimal:hidden"
      :post="post" 
    />
    
    <div class="post w-full font-sans print:text-sm minimal:text-sm">
      <!-- Post wrapper: разные стили -->
      <div class="
        p-4 bg-white dark:bg-black 
        border tweet-border rounded-lg shadow-sm
        print:p-3 print:shadow-none print:border-gray-300
        minimal:p-0 minimal:bg-transparent minimal:border-0
      ">
        <PostHeader />
        <PostBody />
        
        <!-- Media: разные отступы -->
        <div class="mt-2 pl-11 print:pl-0 minimal:pl-0">
          <PostMedia />
        </div>
      </div>

      <!-- Footer: скрыт в экспорте -->
      <PostFooter class="print:hidden minimal:hidden" />
    </div>
  </div>
</template>
```

### Частые паттерны

```vue
<!-- Скрыть в обоих экспортных режимах -->
<div class="print:hidden minimal:hidden">...</div>

<!-- Одинаковое для print и minimal -->
<div class="print:text-sm minimal:text-sm">...</div>

<!-- Разное для print и minimal -->
<div class="
  print:p-3 print:shadow-none
  minimal:p-0 minimal:bg-transparent
">...</div>

<!-- Отступы только в web режиме -->
<div class="pl-11 print:pl-0 minimal:pl-0">...</div>
```

## 🔍 Частые паттерны

### Скрыть UI элементы

```vue
<!-- Кнопки, редакторы, интерактив -->
<button class="print:hidden minimal:hidden">Edit</button>
<div class="controls print:hidden minimal:hidden">Controls</div>
```

### Сбросить декоративные стили

```vue
<div class="
  shadow-lg rounded-xl border-2 
  print:shadow-none print:rounded-none print:border
  minimal:shadow-none minimal:rounded-none minimal:border-0
">
  Content
</div>
```

### Изменить отступы

```vue
<!-- Убрать левый отступ для медиа -->
<div class="pl-11 print:pl-0 minimal:pl-0">
  <img src="..." />
</div>

<!-- Уменьшить внутренние отступы -->
<div class="p-6 print:p-3 minimal:p-0">
  Content
</div>
```

### Изменить размеры шрифта

```vue
<div class="text-base print:text-sm minimal:text-xs">
  Text content
</div>
```

## 💡 Composable API

### useDisplayMode()

```js
import { useDisplayMode } from '~/composables/useDisplayMode'

const { 
  currentMode,     // 'default' | 'minimal'
  isMinimalMode,   // boolean
  isDefaultMode    // boolean
} = useDisplayMode()
```

### Примеры использования

```vue
<script setup>
const { isMinimalMode } = useDisplayMode()

// Условная логика
if (isMinimalMode.value) {
  // Логика для minimal режима
}
</script>

<template>
  <!-- Условный рендеринг -->
  <div v-if="!isMinimalMode">
    Interactive features (только в default режиме)
  </div>
  
  <!-- Условные классы (альтернатива Tailwind вариантам) -->
  <div :class="{ 'hidden': isMinimalMode }">
    Minimal-specific hidden
  </div>
</template>
```

## 🧪 Тестирование

### URLs для тестирования:

```bash
# Default mode (везде)
http://localhost:3000/posts/llamasass

# Minimal mode (IDML preview)
http://localhost:3000/preview/llamasass

# Print mode (срабатывает автоматически)
# 1. При браузерной печати: Ctrl+P (Cmd+P на Mac)
# 2. При генерации PDF на backend (внутренний процесс)
```

### Проверка в DevTools:

```js
// Открыть консоль и проверить data-mode
document.querySelector('[data-mode]').getAttribute('data-mode')
// → "default" | "minimal"
```

## 📊 Сравнение вариантов:

| Вариант | Когда срабатывает | Использование |
|---------|-------------------|---------------|
| `print:` (встроенный) | `@media print` | PDF preview + Ctrl+P |
| `minimal:` (кастомный) | `data-mode="minimal"` | IDML preview |

**Важно:** `print:` работает автоматически при печати, не требует data-mode!

## ✅ Best Practices

1. **Используй `print:` для PDF/печати** - встроенный Tailwind вариант
2. **Используй `minimal:` для IDML preview** - наш кастомный вариант
3. **Комбинируй варианты:** `print:hidden minimal:hidden`
4. **Не дублируй:** если стили одинаковые для print и minimal, применяй оба варианта
5. **Composable:** используй `isMinimalMode` для условной логики

## 🚀 Миграция существующих компонентов

### Шаг 1: Добавить print: и minimal: классы

```vue
<!-- Скрыть в PDF и IDML -->
<div class="print:hidden minimal:hidden">
  UI элементы
</div>

<!-- Разные стили -->
<div class="
  p-4 shadow-lg
  print:p-2 print:shadow-none
  minimal:p-0 minimal:bg-transparent
">
  Контент
</div>
```

### Шаг 2: Протестировать

- Default: визуально проверить в браузере
- Print: нажать Ctrl+P (Cmd+P на Mac)
- Minimal: открыть `/preview/{channel}`

## 📝 Примеры из проекта

### SystemAlert (скрыть в экспорте)

```vue
<SystemAlert 
  class="print:hidden minimal:hidden fixed top-16 right-4 z-50"
/>
```

### Navbar (скрыть в экспорте)

```vue
<nav class="print:hidden minimal:hidden">
  <!-- navigation -->
</nav>
```

### Post wrapper (адаптивные стили)

```vue
<div class="
  post-wrap 
  p-4 bg-white border shadow-sm rounded-lg
  print:p-3 print:shadow-none print:border-gray-300
  minimal:p-0 minimal:bg-transparent minimal:border-0
">
```

---

**Версия:** 2.0  
**Дата:** 30 декабря 2025  
**Изменения в 2.0:** Убран кастомный `paper:` вариант, используется встроенный `print:` вместо него.
