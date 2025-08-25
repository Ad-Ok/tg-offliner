// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  },
  vite: {
    server: {
      allowedHosts: ['localhost', 'ssr'],
    },
  },
  css: [
    '/app/assets/tailwind.css',    // Tailwind через PostCSS
    '/app/assets/styles.scss'      // Ваши SCSS стили
  ],
})
