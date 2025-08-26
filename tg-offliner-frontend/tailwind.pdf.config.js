/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Указываем только компоненты, которые нужны для PDF
    "./app/components/ChannelCover.vue",
    "./app/components/Group.vue", 
    "./app/components/Post.vue",
    "./app/components/PostAuthor.vue",
    "./app/components/PostBody.vue",
    "./app/components/PostFooter.vue",
    "./app/components/PostHeader.vue",
    "./app/components/PostMedia.vue",
    "./app/components/PostFooter.vue",
    "./app/components/PostReactions.vue",
    "./app/components/PrintUtilities.vue", // Файл с print-классами
    "./app/layouts/default.vue", // Layout для применения print:hidden к Navbar
    // Добавляем страницы постов для SSR
    "./app/pages/**/posts.vue"
  ],
  theme: {
    extend: {
      screens: {
        print: { raw: 'print' },    // Стили для печати
        screen: { raw: 'screen' },  // Стили для экрана
      },
      fontFamily: {
        // Определяем безопасные системные шрифты для PDF
        'sans': [
          '-apple-system',
          'BlinkMacSystemFont', 
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif'
        ],
        'serif': [
          'Georgia',
          '"Times New Roman"',
          'Times',
          'serif'
        ],
        'mono': [
          '"SF Mono"',
          'Monaco',
          'Inconsolata',
          '"Roboto Mono"',
          'Consolas',
          '"Courier New"',
          'monospace'
        ]
      }
    },
  },
  // Отключаем DaisyUI для PDF - оно добавляет много ненужных стилей
  plugins: [],
  
  // Минимизируем функциональность
  corePlugins: {
    // Отключаем ненужные для PDF плагины
    animation: false,
    backdropBlur: false,
    backdropBrightness: false,
    backdropContrast: false,
    backdropGrayscale: false,
    backdropHueRotate: false,
    backdropInvert: false,
    backdropOpacity: false,
    backdropSaturate: false,
    backdropSepia: false,
    backgroundAttachment: false,
    blur: false,
    brightness: false,
    contrast: false,
    cursor: false,
    dropShadow: true,
    filter: false,
    grayscale: false,
    hueRotate: false,
    invert: false,
    saturate: false,
    sepia: false,
    transform: true,
    transformOrigin: true,
    transitionDelay: false,
    transitionDuration: false,
    transitionProperty: false,
    transitionTimingFunction: false,
    willChange: false,
    // Оставляем только основные стили для текста и layout
    backgroundColor: true,
    borderColor: true,
    borderRadius: true,
    borderWidth: true,
    textColor: true,
    fontSize: true,
    fontWeight: true,
    margin: true,
    padding: true,
    width: true,
    height: true,
    display: true,
    flexbox: true,
    gap: true,
    overflow: true,
    position: true,
    space: true,
    wordBreak: true,
    whiteSpace: true
  }
}
