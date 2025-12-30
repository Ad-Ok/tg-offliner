/** @type {import('tailwindcss').Config} */
const plugin = require('tailwindcss/plugin')

module.exports = {
  content: [
    "./app/components/**/*.{vue,js,ts}",
    "./app/layouts/**/*.vue", 
    "./app/pages/**/*.vue",
    "./app/plugins/**/*.{js,ts}",
    "./app/app.vue",
    "./app/error.vue"
  ],
  theme: {
    extend: {
      fontFamily: {
        // Синхронизируем шрифты с PDF конфигом для консистентности
        'sans': [
          'Roboto',
          'Arial',
          'Helvetica',
          'sans-serif'
        ],
        'serif': [
          '"Times New Roman"',
          'Times',
          'serif'
        ],
        'mono': [
          '"Courier New"',
          'Courier',
          'monospace'
        ]
      },
    },
  },
  plugins: [
    require("daisyui"),
    
    // Кастомный вариант для IDML режима
    plugin(function({ addVariant }) {
      // minimal: - для IDML preview (минимум стилей)
      addVariant('minimal', '[data-mode="minimal"] &')
    })
  ],
  daisyui: {
    themes: ["light", "dark", "cupcake", "bumblebee", "emerald", "corporate", "synthwave", "retro", "cyberpunk", "valentine", "halloween", "garden", "forest", "aqua", "lofi", "pastel", "fantasy", "wireframe", "black", "luxury", "dracula", "cmyk", "autumn", "business", "acid", "lemonade", "night", "coffee", "winter", "dim", "nord", "sunset"],
  },
}

