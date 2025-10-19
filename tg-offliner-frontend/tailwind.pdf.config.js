/** @type {import('tailwindcss').Config} */
const baseConfig = require('./tailwind.config.js')

module.exports = {
  content: [
    ...baseConfig.content,
    '!./app/components/system/**/*.{vue,js,ts}'
  ],
  theme: {
    extend: {
      screens: {
        print: { raw: 'print' },    // Стили для печати
        screen: { raw: 'screen' },  // Стили для экрана
      },
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
    whiteSpace: true,
    letterSpacing: true,
    lineHeight: true
  }
}
