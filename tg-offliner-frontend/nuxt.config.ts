// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: [
    '@pinia/nuxt'
  ],
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
    '/app/assets/tailwind.css'
  ],
  nitro: {
    devProxy: {
      '/downloads': {
        target: 'http://localhost:5000/downloads',
        changeOrigin: true
      }
    }
  }
})
