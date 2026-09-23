/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        aerotwin: {
          dark: '#0a0d14',
          panel: '#111726',
          border: '#1e293b',
          accent: '#0284c7',
          warning: '#f59e0b',
          danger: '#ef4444',
          success: '#10b981',
          text: '#f8fafc',
          muted: '#94a3b8'
        }
      }
    },
  },
  plugins: [],
}
